/**
 * Social Features Manager
 * Handles friends, messaging, and activity feeds
 */

class SocialManager {
    constructor() {
        this.currentTab = 'friends';
        this.currentChat = null;
        this.activityFeed = 'me';
        this.refreshInterval = null;
    }

    async init() {
        console.log('[Social] Initializing...');

        // Check authentication
        const token = localStorage.getItem('auth_token');
        if (!token) {
            window.location.href = '/login';
            return;
        }

        // Load initial data
        await this.loadFriends();
        await this.loadFriendRequests();
        await this.loadUnreadCount();

        // Start auto-refresh
        this.refreshInterval = setInterval(() => {
            if (this.currentTab === 'friends') {
                this.loadFriends();
                this.loadFriendRequests();
            } else if (this.currentTab === 'messages') {
                this.loadConversations();
                if (this.currentChat) {
                    this.loadConversation(this.currentChat);
                }
            } else if (this.currentTab === 'activity') {
                this.loadActivity();
            }
            this.loadUnreadCount();
        }, 10000);

        console.log('[Social] Ready!');
    }

    switchTab(tab) {
        this.currentTab = tab;

        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        event.target.closest('.tab-btn').classList.add('active');

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        document.getElementById(`${tab}-tab`).classList.add('active');

        // Load data for tab
        if (tab === 'friends') {
            this.loadFriends();
            this.loadFriendRequests();
        } else if (tab === 'messages') {
            this.loadConversations();
        } else if (tab === 'activity') {
            this.loadActivity();
        }
    }

    // ========================================================================
    // FRIENDS MANAGEMENT
    // ========================================================================

    async loadFriends() {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch('/api/social/friends', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const data = await response.json();

            if (data.success) {
                this.renderFriends(data.friends);
            }
        } catch (error) {
            console.error('[Social] Error loading friends:', error);
        }
    }

    renderFriends(friends) {
        const container = document.getElementById('friends-container');
        document.getElementById('friends-count').textContent = friends.length;

        if (friends.length === 0) {
            container.innerHTML = '<p class="text-secondary">No friends yet. Search for users to add!</p>';
            return;
        }

        let html = '';
        friends.forEach(friend => {
            html += `
                <div class="friend-item">
                    <div class="friend-info">
                        <span class="online-indicator ${friend.is_online ? 'online' : ''}"></span>
                        <div>
                            <div class="friend-name">${friend.username}</div>
                            <div class="friend-balance"><i class="bi bi-gem"></i> ${friend.gem_balance.toLocaleString()} GEM</div>
                        </div>
                    </div>
                    <div class="friend-actions">
                        <button class="btn-sm btn-primary" onclick="Social.openChat('${friend.id}', '${friend.username}')">
                            <i class="bi bi-chat"></i> Message
                        </button>
                        <button class="btn-sm btn-danger" onclick="Social.removeFriend('${friend.id}', '${friend.username}')">
                            <i class="bi bi-person-dash"></i> Remove
                        </button>
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    async searchUsers() {
        const query = document.getElementById('user-search').value.trim();
        if (!query) return;

        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch(`/api/social/friends/search?query=${encodeURIComponent(query)}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const data = await response.json();

            if (data.success) {
                this.renderSearchResults(data.users);
            }
        } catch (error) {
            console.error('[Social] Error searching users:', error);
        }
    }

    renderSearchResults(users) {
        const container = document.getElementById('friends-container');

        if (users.length === 0) {
            container.innerHTML = '<p class="text-secondary">No users found</p>';
            return;
        }

        let html = '';
        users.forEach(user => {
            html += `
                <div class="friend-item">
                    <div class="friend-info">
                        <span class="online-indicator ${user.is_online ? 'online' : ''}"></span>
                        <div>
                            <div class="friend-name">${user.username}</div>
                            <div class="friend-balance"><i class="bi bi-gem"></i> ${user.gem_balance.toLocaleString()} GEM</div>
                        </div>
                    </div>
                    <div class="friend-actions">
                        ${user.is_friend ? `
                            <button class="btn-sm btn-primary" onclick="Social.openChat('${user.id}', '${user.username}')">
                                <i class="bi bi-chat"></i> Message
                            </button>
                        ` : user.request_pending ? `
                            <button class="btn-sm btn-sm" disabled>
                                <i class="bi bi-clock"></i> Pending
                            </button>
                        ` : `
                            <button class="btn-sm btn-success" onclick="Social.sendFriendRequest('${user.username}')">
                                <i class="bi bi-person-plus"></i> Add Friend
                            </button>
                        `}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    async sendFriendRequest(username) {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch('/api/social/friends/request', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('success', data.message);
                this.searchUsers(); // Refresh search results
                this.loadFriendRequests(); // Refresh requests
            } else {
                this.showNotification('error', data.message);
            }
        } catch (error) {
            console.error('[Social] Error sending friend request:', error);
            this.showNotification('error', 'Failed to send friend request');
        }
    }

    async loadFriendRequests() {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch('/api/social/friends/requests', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const data = await response.json();

            if (data.success) {
                this.renderFriendRequests(data.received, data.sent);
            }
        } catch (error) {
            console.error('[Social] Error loading friend requests:', error);
        }
    }

    renderFriendRequests(received, sent) {
        // Received requests
        const receivedContainer = document.getElementById('requests-received');
        if (received.length === 0) {
            receivedContainer.innerHTML = '<p class="text-secondary">No pending requests</p>';
        } else {
            let html = '';
            received.forEach(req => {
                html += `
                    <div class="friend-item" style="margin-bottom: 0.5rem;">
                        <div class="friend-info">
                            <div class="friend-name">${req.from_username}</div>
                        </div>
                        <div class="friend-actions">
                            <button class="btn-sm btn-success" onclick="Social.acceptRequest(${req.id})">
                                <i class="bi bi-check"></i>
                            </button>
                            <button class="btn-sm btn-danger" onclick="Social.rejectRequest(${req.id})">
                                <i class="bi bi-x"></i>
                            </button>
                        </div>
                    </div>
                `;
            });
            receivedContainer.innerHTML = html;
        }

        // Sent requests
        const sentContainer = document.getElementById('requests-sent');
        if (sent.length === 0) {
            sentContainer.innerHTML = '<p class="text-secondary">No pending requests</p>';
        } else {
            let html = '';
            sent.forEach(req => {
                html += `
                    <div class="friend-item" style="margin-bottom: 0.5rem;">
                        <div class="friend-info">
                            <div class="friend-name">${req.to_username}</div>
                        </div>
                        <div style="color: var(--text-secondary); font-size: 0.85rem;">
                            <i class="bi bi-clock"></i> Pending
                        </div>
                    </div>
                `;
            });
            sentContainer.innerHTML = html;
        }
    }

    async acceptRequest(requestId) {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch('/api/social/friends/accept', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ request_id: requestId })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('success', data.message);
                this.loadFriends();
                this.loadFriendRequests();
            } else {
                this.showNotification('error', data.message);
            }
        } catch (error) {
            console.error('[Social] Error accepting request:', error);
        }
    }

    async rejectRequest(requestId) {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch('/api/social/friends/reject', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ request_id: requestId })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('success', data.message);
                this.loadFriendRequests();
            } else {
                this.showNotification('error', data.message);
            }
        } catch (error) {
            console.error('[Social] Error rejecting request:', error);
        }
    }

    async removeFriend(friendId, username) {
        if (!confirm(`Remove ${username} from your friends?`)) return;

        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch('/api/social/friends/remove', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ friend_id: friendId })
            });

            const data = await response.json();

            if (data.success) {
                this.showNotification('success', data.message);
                this.loadFriends();
            } else {
                this.showNotification('error', data.message);
            }
        } catch (error) {
            console.error('[Social] Error removing friend:', error);
        }
    }

    // ========================================================================
    // MESSAGING
    // ========================================================================

    async loadConversations() {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch('/api/social/messages/recent', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const data = await response.json();

            if (data.success) {
                this.renderConversations(data.conversations);
            }
        } catch (error) {
            console.error('[Social] Error loading conversations:', error);
        }
    }

    renderConversations(conversations) {
        const container = document.getElementById('conversations-container');

        if (conversations.length === 0) {
            container.innerHTML = '<p class="text-secondary">No conversations yet</p>';
            return;
        }

        let html = '';
        conversations.forEach(conv => {
            html += `
                <div class="conversation-item ${this.currentChat === conv.user_id ? 'active' : ''}"
                     onclick="Social.openChat('${conv.user_id}', '${conv.username}')">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <div class="friend-name">${conv.username}</div>
                            <div class="text-secondary" style="font-size: 0.85rem;">${conv.last_message.substring(0, 30)}...</div>
                        </div>
                        ${conv.unread_count > 0 ? `<span class="unread-badge">${conv.unread_count}</span>` : ''}
                    </div>
                </div>
            `;
        });

        container.innerHTML = html;
    }

    async openChat(userId, username) {
        this.currentChat = userId;

        // Switch to messages tab if not already there
        if (this.currentTab !== 'messages') {
            this.switchTab('messages');
        }

        // Update UI
        document.getElementById('chat-header').textContent = username;
        document.getElementById('message-input').disabled = false;
        document.getElementById('send-btn').disabled = false;

        // Load conversation
        await this.loadConversation(userId);

        // Mark as read
        await this.markAsRead(userId);

        // Update conversations list
        document.querySelectorAll('.conversation-item').forEach(item => item.classList.remove('active'));
        event?.target?.closest('.conversation-item')?.classList.add('active');
    }

    async loadConversation(userId) {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch(`/api/social/messages/conversation/${userId}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const data = await response.json();

            if (data.success) {
                this.renderMessages(data.messages);
            }
        } catch (error) {
            console.error('[Social] Error loading conversation:', error);
        }
    }

    renderMessages(messages) {
        const container = document.getElementById('chat-messages');

        if (messages.length === 0) {
            container.innerHTML = '<p class="text-secondary text-center">No messages yet. Start the conversation!</p>';
            return;
        }

        let html = '';
        messages.forEach(msg => {
            html += `
                <div class="message ${msg.is_mine ? 'mine' : 'theirs'}">
                    ${msg.message}
                </div>
            `;
        });

        container.innerHTML = html;

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }

    async sendMessage() {
        const input = document.getElementById('message-input');
        const message = input.value.trim();

        if (!message || !this.currentChat) return;

        const token = localStorage.getItem('auth_token');

        // Get current chat username
        const username = document.getElementById('chat-header').textContent;

        try {
            const response = await fetch('/api/social/messages/send', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, message })
            });

            const data = await response.json();

            if (data.success) {
                input.value = '';
                await this.loadConversation(this.currentChat);
            } else {
                this.showNotification('error', data.message);
            }
        } catch (error) {
            console.error('[Social] Error sending message:', error);
        }
    }

    async markAsRead(userId) {
        const token = localStorage.getItem('auth_token');

        try {
            await fetch(`/api/social/messages/mark-read/${userId}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });

            this.loadUnreadCount();
        } catch (error) {
            console.error('[Social] Error marking as read:', error);
        }
    }

    async loadUnreadCount() {
        const token = localStorage.getItem('auth_token');

        try {
            const response = await fetch('/api/social/messages/unread-count', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const data = await response.json();

            if (data.success && data.unread_count > 0) {
                const badge = document.getElementById('messages-badge');
                badge.textContent = data.unread_count;
                badge.style.display = 'inline-block';
            } else {
                document.getElementById('messages-badge').style.display = 'none';
            }
        } catch (error) {
            console.error('[Social] Error loading unread count:', error);
        }
    }

    // ========================================================================
    // ACTIVITY FEED
    // ========================================================================

    switchActivityFeed(feed) {
        this.activityFeed = feed;

        // Update buttons
        document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        this.loadActivity();
    }

    async loadActivity() {
        const token = localStorage.getItem('auth_token');
        const endpoint = this.activityFeed === 'me' ? '/api/social/activity/me' : '/api/social/activity/friends';

        try {
            const response = await fetch(endpoint, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            const data = await response.json();

            if (data.success) {
                this.renderActivity(data.activities);
            }
        } catch (error) {
            console.error('[Social] Error loading activity:', error);
        }
    }

    renderActivity(activities) {
        const container = document.getElementById('activity-container');

        if (activities.length === 0) {
            container.innerHTML = '<p class="text-secondary">No activity yet</p>';
            return;
        }

        let html = '';
        activities.forEach(activity => {
            const badgeClass = this.getActivityBadgeClass(activity.activity_type);

            html += `
                <div class="activity-item">
                    <div class="activity-header">
                        <div>
                            ${activity.username ? `<span class="activity-user">${activity.username}</span>` : ''}
                            <span class="activity-badge ${badgeClass}">${activity.activity_type}</span>
                        </div>
                        <span class="activity-time">${this.formatTime(activity.created_at)}</span>
                    </div>
                    <div class="activity-title">${activity.title}</div>
                    ${activity.description ? `<div class="activity-description">${activity.description}</div>` : ''}
                </div>
            `;
        });

        container.innerHTML = html;
    }

    getActivityBadgeClass(type) {
        if (type.includes('win') || type.includes('cashout')) return 'badge-win';
        if (type.includes('achievement')) return 'badge-achievement';
        if (type.includes('level')) return 'badge-level';
        return 'badge-win';
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;

        return date.toLocaleDateString();
    }

    // ========================================================================
    // UTILITIES
    // ========================================================================

    showNotification(type, message) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'success' ? 'var(--success)' : 'var(--error)'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        notification.innerHTML = `
            <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            ${message}
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
    }
}

// Create global instance
const Social = new SocialManager();

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    Social.destroy();
});

// Allow Enter key to send messages
document.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.id === 'message-input') {
        Social.sendMessage();
    }
});
