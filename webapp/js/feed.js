/**
 * NCPS Webapp — Feed Module
 * Renders post feed, handles voting, ranking, and inline expansion.
 */

let feedPosts = [];
let userVotes = {}; // post_id -> vote (+1/-1)
let voteCooldowns = {}; // post_id -> timestamp

// Load saved votes
try {
  const saved = localStorage.getItem('ncps_votes');
  if (saved) userVotes = JSON.parse(saved);
} catch (e) {}

// ═══════════════════════════════════════════════════════
// Feed Loading
// ═══════════════════════════════════════════════════════

async function loadFeed() {
  const container = document.getElementById('feed-container');
  if (!container) return;

  container.innerHTML = '<div class="loading"><div class="spinner"></div><span>Loading feed...</span></div>';

  try {
    const params = {};
    if (currentLocation.lat) {
      params.lat = currentLocation.lat;
      params.lon = currentLocation.lon;
    }

    const query = new URLSearchParams(params).toString();
    const url = '/api/feed' + (query ? '?' + query : '');

    const data = await apiCall(url);
    feedPosts = data.posts;
    renderFeed(feedPosts, container);
  } catch (e) {
    container.innerHTML = '<div class="empty-state"><div class="emoji">⚠️</div><h3>Connection Error</h3><p>' + e.message + '</p></div>';
  }
}

// ═══════════════════════════════════════════════════════
// Feed Rendering
// ═══════════════════════════════════════════════════════

function renderFeed(posts, container) {
  if (posts.length === 0) {
    container.innerHTML = '<div class="empty-state"><div class="emoji">📭</div>' +
      '<h3>No posts yet</h3><p>Be the first to report something! Click "Report" to create a post.</p></div>';
    return;
  }

  container.innerHTML = posts.map((p, i) => renderPostCard(p, i)).join('');
}

function renderPostCard(post, index) {
  const delay = Math.min(index * 0.05, 0.5);
  const credColor = scoreColor(post.credibility);
  const credPct = Math.round(post.credibility * 100);
  const existingVote = userVotes[post.post_id] || 0;

  let html = '<div class="post-card" style="animation-delay:' + delay + 's" id="post-' + post.post_id + '">';

  // Indicators
  if (post.indicators && post.indicators.length > 0) {
    html += '<div class="indicators">';
    post.indicators.forEach(ind => {
      const cls = ind === 'Community Verified' ? 'indicator-verified' :
                  ind === 'Trending' ? 'indicator-trending' :
                  ind === 'Frequently Discussed' ? 'indicator-discussed' :
                  'indicator-recommended';
      const icon = ind === 'Community Verified' ? '✓ ' :
                   ind === 'Trending' ? '🔥 ' :
                   ind === 'Frequently Discussed' ? '💬 ' : '⭐ ';
      html += '<span class="indicator ' + cls + '">' + icon + ind + '</span>';
    });
    html += '</div>';
  }

  // Content
  html += '<div class="post-content">' + escapeHtml(post.content) + '</div>';

  // Credibility bar
  html += '<div class="cred-section">';
  html += '<span class="cred-label">Credibility</span>';
  html += '<div class="cred-bar"><div class="cred-bar-fill" style="width:' + credPct + '%;background:' + credColor + '"></div></div>';
  html += '<span class="cred-value" style="color:' + credColor + '">' + post.credibility.toFixed(2) + '</span>';
  html += '</div>';

  // Meta row
  html += '<div class="post-meta">';
  if (post.urgency >= 0.7) {
    html += '<span class="post-meta-item"><span class="emoji">🔴</span> Urgent</span>';
  } else if (post.urgency >= 0.4) {
    html += '<span class="post-meta-item"><span class="emoji">🟡</span> Medium priority</span>';
  }
  if (post.distance_m !== null && post.distance_m !== undefined) {
    html += '<span class="post-meta-item"><span class="emoji">📍</span> ' + formatDistance(post.distance_m) + '</span>';
  }
  if (post.variance < 0.1) {
    html += '<span class="post-meta-item"><span class="emoji">✅</span> Stable</span>';
  }
  html += '<span class="post-meta-item">' + timeAgo(post.created_at) + '</span>';
  html += '</div>';

  // Vote section
  html += '<div class="vote-section">';
  html += '<button class="vote-btn' + (existingVote === 1 ? ' active-up' : '') +
    '" onclick="doVote(\'' + post.post_id + '\', 1)" ' +
    (existingVote !== 0 ? 'disabled' : '') + '>' +
    '👍 Credible</button>';
  html += '<button class="vote-btn' + (existingVote === -1 ? ' active-down' : '') +
    '" onclick="doVote(\'' + post.post_id + '\', -1)" ' +
    (existingVote !== 0 ? 'disabled' : '') + '>' +
    '👎 Doubt</button>';
  html += '<div class="vote-spacer"></div>';
  html += '<span class="vote-count">' + post.vote_count + ' votes · ' + post.n_effective.toFixed(1) + ' effective</span>';
  html += '</div>';

  html += '</div>';
  return html;
}

// ═══════════════════════════════════════════════════════
// Voting
// ═══════════════════════════════════════════════════════

async function doVote(postId, vote) {
  // Anti-spam cooldown (3 seconds)
  const now = Date.now();
  if (voteCooldowns[postId] && now - voteCooldowns[postId] < 3000) {
    showToast('Please wait before voting again', 'error');
    return;
  }
  voteCooldowns[postId] = now;

  // Optimistic update
  userVotes[postId] = vote;
  localStorage.setItem('ncps_votes', JSON.stringify(userVotes));

  const card = document.getElementById('post-' + postId);
  if (card) {
    const btns = card.querySelectorAll('.vote-btn');
    btns.forEach(btn => btn.disabled = true);
    if (vote === 1) btns[0].classList.add('active-up');
    if (vote === -1) btns[1].classList.add('active-down');
  }

  try {
    const result = await apiCall('/api/post/vote', 'POST', {
      user_id: getUserId(),
      post_id: postId,
      vote: vote,
    });

    // Update credibility in UI
    if (card && result.updated_credibility !== undefined) {
      const credEl = card.querySelector('.cred-value');
      const fillEl = card.querySelector('.cred-bar-fill');
      if (credEl) {
        const color = scoreColor(result.updated_credibility);
        credEl.textContent = result.updated_credibility.toFixed(2);
        credEl.style.color = color;
        if (fillEl) {
          fillEl.style.width = (result.updated_credibility * 100) + '%';
          fillEl.style.background = color;
        }
      }
    }

    showToast('Vote recorded — credibility updated', 'success');
  } catch (e) {
    showToast('Failed to record vote: ' + e.message, 'error');
    // Rollback
    delete userVotes[postId];
    localStorage.setItem('ncps_votes', JSON.stringify(userVotes));
  }
}

// ═══════════════════════════════════════════════════════
// Auto-refresh
// ═══════════════════════════════════════════════════════

function startAutoRefresh(intervalMs = 30000) {
  setInterval(() => {
    loadFeed();
  }, intervalMs);
}
