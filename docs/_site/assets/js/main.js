// Main JavaScript for Terry-Form MCP Documentation

// Mobile navigation toggle
document.addEventListener('DOMContentLoaded', function() {
  const navToggle = document.querySelector('.nav-toggle');
  const navMenu = document.querySelector('.nav-menu');
  
  if (navToggle && navMenu) {
    navToggle.addEventListener('click', function() {
      navMenu.classList.toggle('active');
      navToggle.classList.toggle('active');
    });
  }
  
  // Close mobile menu when clicking outside
  document.addEventListener('click', function(event) {
    if (!event.target.closest('.nav-container')) {
      navMenu?.classList.remove('active');
      navToggle?.classList.remove('active');
    }
  });
});

// Smooth scroll for anchor links
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

// Copy code button for code blocks
document.addEventListener('DOMContentLoaded', function() {
  const codeBlocks = document.querySelectorAll('pre code');
  
  codeBlocks.forEach(block => {
    const pre = block.parentElement;
    const wrapper = document.createElement('div');
    wrapper.className = 'code-wrapper';
    pre.parentNode.insertBefore(wrapper, pre);
    wrapper.appendChild(pre);
    
    const button = document.createElement('button');
    button.className = 'copy-button';
    button.innerHTML = '<i class="fas fa-copy"></i> Copy';
    wrapper.appendChild(button);
    
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(block.textContent);
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.add('copied');
        
        setTimeout(() => {
          button.innerHTML = '<i class="fas fa-copy"></i> Copy';
          button.classList.remove('copied');
        }, 2000);
      } catch (err) {
        console.error('Failed to copy:', err);
      }
    });
  });
});

// Table of Contents generation
document.addEventListener('DOMContentLoaded', function() {
  const tocContainer = document.querySelector('.toc');
  if (!tocContainer) return;
  
  const headings = document.querySelectorAll('h2, h3, h4');
  if (headings.length === 0) return;
  
  const toc = document.createElement('nav');
  toc.className = 'table-of-contents';
  
  const tocTitle = document.createElement('h4');
  tocTitle.textContent = 'On this page';
  toc.appendChild(tocTitle);
  
  const tocList = document.createElement('ul');
  
  headings.forEach(heading => {
    const id = heading.id || heading.textContent.toLowerCase().replace(/\s+/g, '-');
    heading.id = id;
    
    const li = document.createElement('li');
    li.className = `toc-${heading.tagName.toLowerCase()}`;
    
    const a = document.createElement('a');
    a.href = `#${id}`;
    a.textContent = heading.textContent;
    
    li.appendChild(a);
    tocList.appendChild(li);
  });
  
  toc.appendChild(tocList);
  tocContainer.appendChild(toc);
});

// Search functionality (basic implementation)
document.addEventListener('DOMContentLoaded', function() {
  const searchInput = document.querySelector('.search-input');
  const searchResults = document.querySelector('.search-results');
  
  if (!searchInput || !searchResults) return;
  
  let searchIndex = [];
  
  // Load search index
  fetch('/search.json')
    .then(response => response.json())
    .then(data => {
      searchIndex = data;
    })
    .catch(err => console.error('Failed to load search index:', err));
  
  // Debounce function
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }
  
  // Search function
  function performSearch(query) {
    if (query.length < 3) {
      searchResults.innerHTML = '';
      searchResults.classList.remove('active');
      return;
    }
    
    const results = searchIndex.filter(item => {
      const searchText = `${item.title} ${item.content}`.toLowerCase();
      return searchText.includes(query.toLowerCase());
    });
    
    if (results.length === 0) {
      searchResults.innerHTML = '<p class="no-results">No results found</p>';
    } else {
      searchResults.innerHTML = results.slice(0, 10).map(result => `
        <a href="${result.url}" class="search-result">
          <h5>${result.title}</h5>
          <p>${result.excerpt}</p>
        </a>
      `).join('');
    }
    
    searchResults.classList.add('active');
  }
  
  // Debounced search
  const debouncedSearch = debounce(performSearch, 300);
  
  searchInput.addEventListener('input', (e) => {
    debouncedSearch(e.target.value);
  });
  
  // Close search results when clicking outside
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-container')) {
      searchResults.classList.remove('active');
    }
  });
});

// Dark mode toggle
document.addEventListener('DOMContentLoaded', function() {
  const darkModeToggle = document.querySelector('.dark-mode-toggle');
  if (!darkModeToggle) return;
  
  const currentTheme = localStorage.getItem('theme') || 'auto';
  
  if (currentTheme === 'dark') {
    document.documentElement.classList.add('dark-mode');
  } else if (currentTheme === 'light') {
    document.documentElement.classList.remove('dark-mode');
  }
  
  darkModeToggle.addEventListener('click', () => {
    const isDark = document.documentElement.classList.toggle('dark-mode');
    localStorage.setItem('theme', isDark ? 'dark' : 'light');
  });
});

// Add copy button styles
const style = document.createElement('style');
style.textContent = `
  .code-wrapper {
    position: relative;
  }
  
  .copy-button {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    padding: 0.25rem 0.5rem;
    background: #2196F3;
    color: white;
    border: none;
    border-radius: 0.25rem;
    font-size: 0.875rem;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;
  }
  
  .code-wrapper:hover .copy-button {
    opacity: 1;
  }
  
  .copy-button:hover {
    background: #1976D2;
  }
  
  .copy-button.copied {
    background: #4CAF50;
  }
  
  .table-of-contents {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 2rem;
  }
  
  .table-of-contents h4 {
    margin-top: 0;
    margin-bottom: 0.5rem;
  }
  
  .table-of-contents ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  
  .table-of-contents li {
    margin: 0.25rem 0;
  }
  
  .toc-h3 {
    padding-left: 1rem;
  }
  
  .toc-h4 {
    padding-left: 2rem;
  }
  
  .table-of-contents a {
    color: #333;
    text-decoration: none;
  }
  
  .table-of-contents a:hover {
    color: #2196F3;
  }
  
  @media (prefers-color-scheme: dark) {
    .table-of-contents {
      background: #2a2a2a;
    }
    
    .table-of-contents a {
      color: #e0e0e0;
    }
  }
`;
document.head.appendChild(style);