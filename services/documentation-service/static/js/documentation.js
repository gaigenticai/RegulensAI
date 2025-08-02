/**
 * RegulateAI Documentation Interactive JavaScript
 * Provides search functionality, navigation enhancements, and user experience improvements
 */

class DocumentationApp {
    constructor() {
        this.searchInput = document.getElementById('searchInput');
        this.searchSuggestions = document.getElementById('searchSuggestions');
        this.searchForm = document.getElementById('searchForm');
        this.searchTimeout = null;
        this.currentSearchQuery = '';
        
        this.init();
    }

    init() {
        this.setupSearch();
        this.setupNavigation();
        this.setupCodeBlocks();
        this.setupTooltips();
        this.setupScrollSpy();
        this.setupKeyboardShortcuts();
        
        console.log('RegulateAI Documentation App initialized');
    }

    /**
     * Setup interactive search functionality
     */
    setupSearch() {
        if (!this.searchInput) return;

        // Real-time search suggestions
        this.searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            if (this.searchTimeout) {
                clearTimeout(this.searchTimeout);
            }

            if (query.length >= 2) {
                this.searchTimeout = setTimeout(() => {
                    this.fetchSearchSuggestions(query);
                }, 300);
            } else {
                this.hideSuggestions();
            }
        });

        // Handle search form submission
        if (this.searchForm) {
            this.searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const query = this.searchInput.value.trim();
                if (query) {
                    this.performSearch(query);
                }
            });
        }

        // Handle keyboard navigation in suggestions
        this.searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateSuggestions(e.key === 'ArrowDown' ? 1 : -1);
            } else if (e.key === 'Enter') {
                const selected = this.searchSuggestions.querySelector('.suggestion-selected');
                if (selected) {
                    e.preventDefault();
                    this.selectSuggestion(selected);
                }
            } else if (e.key === 'Escape') {
                this.hideSuggestions();
            }
        });

        // Hide suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container')) {
                this.hideSuggestions();
            }
        });
    }

    /**
     * Fetch search suggestions from API
     */
    async fetchSearchSuggestions(query) {
        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    limit: 5
                })
            });

            if (response.ok) {
                const data = await response.json();
                this.displaySuggestions(data.results, query);
            }
        } catch (error) {
            console.error('Search suggestions failed:', error);
        }
    }

    /**
     * Display search suggestions
     */
    displaySuggestions(results, query) {
        if (!this.searchSuggestions || results.length === 0) {
            this.hideSuggestions();
            return;
        }

        const suggestionsHtml = results.map((result, index) => `
            <div class="search-suggestion ${index === 0 ? 'suggestion-selected' : ''}" 
                 data-url="${result.url}" data-title="${result.title}">
                <div class="suggestion-title">
                    <i class="fas fa-${this.getIconForCategory(result.category)} me-2"></i>
                    ${this.highlightQuery(result.title, query)}
                </div>
                <div class="suggestion-content text-muted small">
                    ${this.highlightQuery(result.content, query)}
                </div>
                <div class="suggestion-meta text-muted small">
                    <span class="badge bg-secondary me-1">${result.category}</span>
                    <span class="badge bg-info">${result.service}</span>
                </div>
            </div>
        `).join('');

        this.searchSuggestions.innerHTML = suggestionsHtml;
        this.searchSuggestions.style.display = 'block';

        // Add click handlers to suggestions
        this.searchSuggestions.querySelectorAll('.search-suggestion').forEach(suggestion => {
            suggestion.addEventListener('click', () => {
                this.selectSuggestion(suggestion);
            });
        });
    }

    /**
     * Navigate through suggestions with keyboard
     */
    navigateSuggestions(direction) {
        const suggestions = this.searchSuggestions.querySelectorAll('.search-suggestion');
        const current = this.searchSuggestions.querySelector('.suggestion-selected');
        
        if (suggestions.length === 0) return;

        let newIndex = 0;
        if (current) {
            const currentIndex = Array.from(suggestions).indexOf(current);
            newIndex = currentIndex + direction;
            
            if (newIndex < 0) newIndex = suggestions.length - 1;
            if (newIndex >= suggestions.length) newIndex = 0;
            
            current.classList.remove('suggestion-selected');
        }

        suggestions[newIndex].classList.add('suggestion-selected');
    }

    /**
     * Select a suggestion
     */
    selectSuggestion(suggestion) {
        const url = suggestion.dataset.url;
        const title = suggestion.dataset.title;
        
        this.searchInput.value = title;
        this.hideSuggestions();
        
        // Navigate to the selected page
        window.location.href = url;
    }

    /**
     * Hide search suggestions
     */
    hideSuggestions() {
        if (this.searchSuggestions) {
            this.searchSuggestions.style.display = 'none';
        }
    }

    /**
     * Perform search and navigate to results
     */
    performSearch(query) {
        window.location.href = `/search?q=${encodeURIComponent(query)}`;
    }

    /**
     * Highlight query terms in text
     */
    highlightQuery(text, query) {
        if (!query || !text) return text;
        
        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<span class="search-highlight">$1</span>');
    }

    /**
     * Get icon for category
     */
    getIconForCategory(category) {
        const icons = {
            'Security': 'shield-alt',
            'Compliance': 'check-circle',
            'API Reference': 'code',
            'Test Results': 'vial',
            'Database': 'database',
            'Configuration': 'cog',
            'General': 'file-alt'
        };
        return icons[category] || 'file-alt';
    }

    /**
     * Setup navigation enhancements
     */
    setupNavigation() {
        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        // Active navigation highlighting
        this.updateActiveNavigation();
        window.addEventListener('scroll', () => {
            this.updateActiveNavigation();
        });

        // Mobile navigation toggle
        const navToggle = document.querySelector('.navbar-toggler');
        if (navToggle) {
            navToggle.addEventListener('click', () => {
                document.body.classList.toggle('nav-open');
            });
        }
    }

    /**
     * Update active navigation based on scroll position
     */
    updateActiveNavigation() {
        const sections = document.querySelectorAll('section[id], div[id]');
        const navLinks = document.querySelectorAll('.sidebar .nav-link');
        
        let current = '';
        sections.forEach(section => {
            const sectionTop = section.offsetTop;
            const sectionHeight = section.clientHeight;
            if (window.pageYOffset >= sectionTop - 200) {
                current = section.getAttribute('id');
            }
        });

        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === `#${current}`) {
                link.classList.add('active');
            }
        });
    }

    /**
     * Setup code block enhancements
     */
    setupCodeBlocks() {
        // Add copy buttons to code blocks
        document.querySelectorAll('pre code').forEach(codeBlock => {
            const pre = codeBlock.parentElement;
            const copyButton = document.createElement('button');
            copyButton.className = 'btn btn-sm btn-outline-secondary copy-code-btn';
            copyButton.innerHTML = '<i class="fas fa-copy"></i>';
            copyButton.title = 'Copy code';
            
            copyButton.addEventListener('click', () => {
                this.copyToClipboard(codeBlock.textContent);
                copyButton.innerHTML = '<i class="fas fa-check text-success"></i>';
                setTimeout(() => {
                    copyButton.innerHTML = '<i class="fas fa-copy"></i>';
                }, 2000);
            });

            pre.style.position = 'relative';
            copyButton.style.position = 'absolute';
            copyButton.style.top = '0.5rem';
            copyButton.style.right = '0.5rem';
            
            pre.appendChild(copyButton);
        });

        // Syntax highlighting for JSON examples
        document.querySelectorAll('code.language-json').forEach(codeBlock => {
            try {
                const json = JSON.parse(codeBlock.textContent);
                codeBlock.innerHTML = this.syntaxHighlightJson(json);
            } catch (e) {
                // If not valid JSON, leave as is
            }
        });
    }

    /**
     * Copy text to clipboard
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
        } catch (err) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
        }
    }

    /**
     * Syntax highlight JSON
     */
    syntaxHighlightJson(json) {
        if (typeof json !== 'string') {
            json = JSON.stringify(json, undefined, 2);
        }
        
        json = json.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        
        return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return '<span class="' + cls + '">' + match + '</span>';
        });
    }

    /**
     * Setup tooltips
     */
    setupTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    /**
     * Setup scroll spy for table of contents
     */
    setupScrollSpy() {
        const tocLinks = document.querySelectorAll('.table-of-contents a');
        if (tocLinks.length === 0) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const id = entry.target.getAttribute('id');
                const tocLink = document.querySelector(`.table-of-contents a[href="#${id}"]`);
                
                if (entry.isIntersecting) {
                    tocLinks.forEach(link => link.classList.remove('active'));
                    if (tocLink) tocLink.classList.add('active');
                }
            });
        }, {
            rootMargin: '-20% 0px -35% 0px'
        });

        document.querySelectorAll('h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]').forEach(heading => {
            observer.observe(heading);
        });
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K to focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                if (this.searchInput) {
                    this.searchInput.focus();
                    this.searchInput.select();
                }
            }
            
            // Escape to clear search
            if (e.key === 'Escape' && document.activeElement === this.searchInput) {
                this.searchInput.blur();
                this.hideSuggestions();
            }
        });
    }
}

// Initialize the documentation app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new DocumentationApp();
});

// Additional utility functions
window.DocumentationUtils = {
    /**
     * Format timestamp for display
     */
    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
    },

    /**
     * Generate table of contents
     */
    generateTOC(container) {
        const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6');
        if (headings.length === 0) return;

        const toc = document.createElement('div');
        toc.className = 'table-of-contents';
        toc.innerHTML = '<h6>Table of Contents</h6>';

        const list = document.createElement('ul');
        list.className = 'list-unstyled';

        headings.forEach((heading, index) => {
            if (!heading.id) {
                heading.id = `heading-${index}`;
            }

            const li = document.createElement('li');
            li.className = `toc-${heading.tagName.toLowerCase()}`;
            
            const link = document.createElement('a');
            link.href = `#${heading.id}`;
            link.textContent = heading.textContent;
            link.className = 'text-decoration-none';
            
            li.appendChild(link);
            list.appendChild(li);
        });

        toc.appendChild(list);
        container.insertBefore(toc, container.firstChild);
    },

    /**
     * Expand/collapse sections
     */
    toggleSection(button) {
        const section = button.nextElementSibling;
        const icon = button.querySelector('i');
        
        if (section.style.display === 'none') {
            section.style.display = 'block';
            icon.className = 'fas fa-chevron-up';
            button.setAttribute('aria-expanded', 'true');
        } else {
            section.style.display = 'none';
            icon.className = 'fas fa-chevron-down';
            button.setAttribute('aria-expanded', 'false');
        }
    }
};
