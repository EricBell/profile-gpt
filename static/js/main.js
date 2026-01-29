// Copyright Polymorph Corporation (2026)

/**
 * ProfileGPT - Main Application JavaScript
 * Handles chat and job vetting functionality
 */

(function() {
    'use strict';

    // Get config from data attributes
    const config = {
        maxQueries: parseInt(document.body.dataset.maxQueries, 10),
        queryCount: parseInt(document.body.dataset.queryCount, 10)
    };

    // View elements
    const modeSelection = document.getElementById('mode-selection');
    const chatView = document.getElementById('chat-view');
    const vettingView = document.getElementById('vetting-view');

    // Chat elements
    const chatContainer = document.getElementById('chat-container');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const queryCountEl = document.getElementById('query-count');
    const errorContainer = document.getElementById('error-container');
    const welcome = document.getElementById('welcome');

    // Vetting elements
    const jobDescription = document.getElementById('job-description');
    const analyzeButton = document.getElementById('analyze-button');
    const vettingResults = document.getElementById('vetting-results');
    const vettingError = document.getElementById('vetting-error');

    let isLoading = false;
    let isAnalyzing = false;

    // View switching
    function showView(view) {
        modeSelection.style.display = 'none';
        chatView.classList.remove('active');
        vettingView.classList.remove('active');

        if (view === 'mode') {
            modeSelection.style.display = 'flex';
        } else if (view === 'chat') {
            chatView.classList.add('active');
            messageInput.focus();
        } else if (view === 'vetting') {
            vettingView.classList.add('active');
            jobDescription.focus();
        }
    }

    // Chat functionality
    function autoResize() {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function addMessage(role, content) {
        if (welcome) {
            welcome.style.display = 'none';
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message ' + role;

        const roleLabel = role === 'user' ? 'You' : 'Eric';
        messageDiv.innerHTML =
            '<div class="message-role">' + roleLabel + '</div>' +
            '<div class="message-content">' + escapeHtml(content) + '</div>';

        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function showError(message) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        setTimeout(function() {
            errorContainer.style.display = 'none';
        }, 5000);
    }

    function setLoading(loading) {
        isLoading = loading;
        sendButton.disabled = loading;
        messageInput.disabled = loading;

        if (loading) {
            sendButton.innerHTML = '<span class="loading"></span>';
        } else {
            sendButton.innerHTML =
                '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">' +
                '<path d="M22 2L11 13M22 2L15 22L11 13M11 13L2 9L22 2"/>' +
                '</svg>';
        }
    }

    function disableInput(message) {
        messageInput.disabled = true;
        sendButton.disabled = true;
        messageInput.placeholder = message;
    }

    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message || isLoading) return;

        addMessage('user', message);
        messageInput.value = '';
        autoResize();
        setLoading(true);

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            });

            const data = await response.json();

            if (response.ok) {
                addMessage('assistant', data.response);
                queryCountEl.textContent = data.query_count;

                if (data.query_count >= config.maxQueries) {
                    disableInput('Query limit reached for this session');
                }
            } else if (response.status === 429) {
                disableInput('Query limit reached for this session');
                showError(data.message);
            } else {
                showError(data.message || data.error || 'An error occurred');
            }
        } catch (error) {
            showError('Failed to send message. Please try again.');
        } finally {
            setLoading(false);
        }
    }

    /**
     * Handle suggestion button clicks
     * Auto-submits a pre-defined question
     */
    function submitSuggestion(suggestionText) {
        // If not in chat view, switch to it first
        if (!chatView.classList.contains('active')) {
            showView('chat');
        }

        // Set the message input value
        messageInput.value = suggestionText;

        // Auto-submit the message
        sendMessage();
    }

    // Vetting functionality
    function showVettingError(message) {
        vettingError.textContent = message;
        vettingError.style.display = 'block';
        setTimeout(function() {
            vettingError.style.display = 'none';
        }, 5000);
    }

    function setAnalyzing(analyzing) {
        isAnalyzing = analyzing;
        analyzeButton.disabled = analyzing;
        jobDescription.disabled = analyzing;
        analyzeButton.textContent = analyzing ? 'Analyzing...' : 'Analyze Match';
    }

    function getMatchCategory(score) {
        if (score >= 85) return 'Strong Match';
        if (score >= 70) return 'Good Match';
        if (score >= 50) return 'Partial Match';
        return 'Limited Match';
    }

    function getScoreClass(score) {
        if (score >= 85) return 'strong';
        if (score >= 70) return 'good';
        if (score >= 50) return 'partial';
        return 'limited';
    }

    function displayResults(data) {
        vettingResults.classList.add('active');

        // Overall score
        const scoreCircle = document.getElementById('score-circle');
        scoreCircle.className = 'score-circle ' + getScoreClass(data.overall_score);
        document.getElementById('overall-score-value').textContent = data.overall_score;
        document.getElementById('match-category').textContent = getMatchCategory(data.overall_score);

        // Sub scores
        document.getElementById('skills-score').textContent = data.skills_match + '%';
        document.getElementById('skills-bar').style.width = data.skills_match + '%';

        document.getElementById('experience-score').textContent = data.experience_match + '%';
        document.getElementById('experience-bar').style.width = data.experience_match + '%';

        document.getElementById('role-score').textContent = data.role_fit + '%';
        document.getElementById('role-bar').style.width = data.role_fit + '%';

        // Summary
        document.getElementById('summary-text').textContent = data.summary;
        document.getElementById('recommendation-text').textContent = data.recommendation;

        // Strengths
        const strengthsList = document.getElementById('strengths-list');
        strengthsList.innerHTML = '';
        (data.strengths || []).forEach(function(s) {
            const li = document.createElement('li');
            li.textContent = s;
            strengthsList.appendChild(li);
        });

        // Gaps
        const gapsList = document.getElementById('gaps-list');
        gapsList.innerHTML = '';
        (data.gaps || []).forEach(function(g) {
            const li = document.createElement('li');
            li.textContent = g;
            gapsList.appendChild(li);
        });
    }

    async function analyzeJob() {
        const description = jobDescription.value.trim();
        if (!description || isAnalyzing) return;

        setAnalyzing(true);
        vettingResults.classList.remove('active');

        try {
            const response = await fetch('/vet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ job_description: description }),
            });

            const data = await response.json();

            if (response.ok) {
                displayResults(data);
            } else {
                showVettingError(data.message || data.error || 'Analysis failed');
            }
        } catch (error) {
            showVettingError('Failed to analyze. Please try again.');
        } finally {
            setAnalyzing(false);
        }
    }

    // Event listeners
    document.getElementById('chat-mode-btn').addEventListener('click', function() {
        showView('chat');
    });
    document.getElementById('vetting-mode-btn').addEventListener('click', function() {
        showView('vetting');
    });
    document.getElementById('chat-back-btn').addEventListener('click', function() {
        showView('mode');
    });
    document.getElementById('vetting-back-btn').addEventListener('click', function() {
        showView('mode');
    });

    messageInput.addEventListener('input', autoResize);
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    analyzeButton.addEventListener('click', analyzeJob);

    // Suggestion button handlers
    document.querySelectorAll('.suggestion-link, .suggestion-button').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const suggestion = this.dataset.suggestion || this.textContent.trim();
            submitSuggestion(suggestion);
        });
    });

    // Check initial status
    if (config.queryCount >= config.maxQueries) {
        disableInput('Query limit reached for this session');
    }
})();
