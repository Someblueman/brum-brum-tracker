/**
 * Authentication handler for Brum Brum Tracker
 * 
 * Manages authentication state and handles login/token storage
 */

class AuthHandler {
    constructor() {
        this.token = localStorage.getItem('brumbrumToken');
        this.isAuthenticated = false;
        this.loginCallback = null;
        this.authRequired = false;
    }

    /**
     * Set callback for when login is needed
     */
    onLoginRequired(callback) {
        this.loginCallback = callback;
    }

    /**
     * Handle authentication-related WebSocket messages
     */
    handleAuthMessage(data) {
        switch (data.type) {
            case 'auth_required':
                this.authRequired = true;
                // Try token auth first if available
                if (this.token) {
                    return {
                        type: 'auth_token',
                        token: this.token
                    };
                } else if (this.loginCallback) {
                    // Show login UI
                    this.loginCallback();
                }
                break;

            case 'auth_response':
                if (data.success) {
                    this.isAuthenticated = true;
                    if (data.token) {
                        this.token = data.token;
                        localStorage.setItem('brumbrumToken', data.token);
                    }
                    // Hide login UI if shown
                    this.hideLoginUI();
                } else {
                    // Authentication failed
                    this.isAuthenticated = false;
                    if (data.message.includes('token')) {
                        // Token invalid, clear it
                        this.clearToken();
                        if (this.loginCallback) {
                            this.loginCallback();
                        }
                    } else {
                        // Login failed, show error
                        this.showLoginError(data.message);
                    }
                }
                break;
        }
        return null;
    }

    /**
     * Perform login with credentials
     */
    login(username, password) {
        return {
            type: 'auth_login',
            username: username,
            password: password
        };
    }

    /**
     * Clear stored token
     */
    clearToken() {
        this.token = null;
        this.isAuthenticated = false;
        localStorage.removeItem('brumbrumToken');
    }

    /**
     * Create and show login UI
     */
    showLoginUI() {
        // Remove existing login UI if any
        this.hideLoginUI();

        const loginOverlay = document.createElement('div');
        loginOverlay.id = 'auth-overlay';
        loginOverlay.innerHTML = `
            <div id="auth-container">
                <h2>Login Required</h2>
                <p>Please enter your credentials to access Brum Brum Tracker</p>
                <form id="auth-form">
                    <input 
                        type="text" 
                        id="auth-username" 
                        placeholder="Username" 
                        required
                        autocomplete="username"
                    >
                    <input 
                        type="password" 
                        id="auth-password" 
                        placeholder="Password" 
                        required
                        autocomplete="current-password"
                    >
                    <button type="submit">Login</button>
                    <div id="auth-error" class="error-message"></div>
                </form>
            </div>
        `;

        // Add styles
        const style = document.createElement('style');
        style.textContent = `
            #auth-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 10000;
            }

            #auth-container {
                background: white;
                padding: 40px;
                border-radius: 20px;
                max-width: 400px;
                width: 90%;
                text-align: center;
                font-family: 'Fredoka One', cursive;
            }

            #auth-container h2 {
                color: #3b82f6;
                margin-bottom: 10px;
                font-size: 2rem;
            }

            #auth-container p {
                color: #666;
                margin-bottom: 30px;
            }

            #auth-form {
                display: flex;
                flex-direction: column;
                gap: 15px;
            }

            #auth-form input {
                padding: 15px 20px;
                font-size: 16px;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                font-family: inherit;
                transition: border-color 0.3s;
            }

            #auth-form input:focus {
                outline: none;
                border-color: #3b82f6;
            }

            #auth-form button {
                padding: 15px 30px;
                font-size: 18px;
                font-family: 'Fredoka One', cursive;
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 10px;
                cursor: pointer;
                transition: background 0.3s;
            }

            #auth-form button:hover {
                background: #2563eb;
            }

            .error-message {
                color: #f44336;
                font-size: 14px;
                margin-top: 10px;
                min-height: 20px;
            }
        `;
        document.head.appendChild(style);
        document.body.appendChild(loginOverlay);

        // Handle form submission
        const form = document.getElementById('auth-form');
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            const username = document.getElementById('auth-username').value;
            const password = document.getElementById('auth-password').value;
            
            // Send login message through WebSocket
            if (window.websocket && window.websocket.readyState === WebSocket.OPEN) {
                const loginMessage = this.login(username, password);
                window.websocket.send(JSON.stringify(loginMessage));
            }
        });
    }

    /**
     * Hide login UI
     */
    hideLoginUI() {
        const overlay = document.getElementById('auth-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * Show login error message
     */
    showLoginError(message) {
        const errorDiv = document.getElementById('auth-error');
        if (errorDiv) {
            errorDiv.textContent = message;
            // Clear error after 5 seconds
            setTimeout(() => {
                errorDiv.textContent = '';
            }, 5000);
        }
    }
}

// Export for use in main.js
window.AuthHandler = AuthHandler;