/**
 * Terry-Form MCP Documentation - Main JavaScript
 * Handles navigation, code copying, TOC generation, and other interactive features
 */

(function() {
  'use strict';

  // Mobile navigation toggle
  function initMobileNav() {
    const navToggle = document.querySelector('.nav-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (!navToggle || !navMenu) return;

    navToggle.addEventListener('click', function() {
      const isExpanded = navMenu.classList.toggle('active');
      navToggle.classList.toggle('active');
      navToggle.setAttribute('aria-expanded', isExpanded);
    });

    // Close mobile menu when clicking outside
    document.addEventListener('click', function(event) {
      if (!event.target.closest('.nav-container')) {
        navMenu.classList.remove('active');
        navToggle.classList.remove('active');
        navToggle.setAttribute('aria-expanded', 'false');
      }
    });

    // Close mobile menu on escape key
    document.addEventListener('keydown', function(event) {
      if (event.key === 'Escape' && navMenu.classList.contains('active')) {
        navMenu.classList.remove('active');
        navToggle.classList.remove('active');
        navToggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Smooth scroll for anchor links
  function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;

        const target = document.querySelector(targetId);
        if (target) {
          e.preventDefault();
          const navHeight = document.querySelector('.main-nav')?.offsetHeight || 0;
          const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight - 20;

          window.scrollTo({
            top: targetPosition,
            behavior: 'smooth'
          });

          // Update URL without jumping
          history.pushState(null, null, targetId);
        }
      });
    });
  }

  // Copy code button for code blocks
  function initCodeCopy() {
    const codeBlocks = document.querySelectorAll('pre code');

    codeBlocks.forEach(block => {
      const pre = block.parentElement;

      // Skip if already has copy button
      if (pre.querySelector('.code-copy-btn')) return;

      const button = document.createElement('button');
      button.className = 'code-copy-btn';
      button.innerHTML = 'Copy';
      button.setAttribute('aria-label', 'Copy code to clipboard');
      pre.appendChild(button);

      button.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(block.textContent);
          button.innerHTML = 'Copied!';
          button.classList.add('copied');

          setTimeout(() => {
            button.innerHTML = 'Copy';
            button.classList.remove('copied');
          }, 2000);
        } catch (err) {
          // Fallback for older browsers
          const textArea = document.createElement('textarea');
          textArea.value = block.textContent;
          textArea.style.position = 'fixed';
          textArea.style.left = '-9999px';
          document.body.appendChild(textArea);
          textArea.select();

          try {
            document.execCommand('copy');
            button.innerHTML = 'Copied!';
            button.classList.add('copied');

            setTimeout(() => {
              button.innerHTML = 'Copy';
              button.classList.remove('copied');
            }, 2000);
          } catch (e) {
            console.error('Failed to copy:', e);
          }

          document.body.removeChild(textArea);
        }
      });
    });
  }

  // Table of Contents generation
  function initTableOfContents() {
    const tocContainer = document.querySelector('.toc');
    if (!tocContainer) return;

    const contentArea = document.querySelector('.guide-body, .tutorial-content, .api-content, .main-content');
    if (!contentArea) return;

    const headings = contentArea.querySelectorAll('h2, h3');
    if (headings.length === 0) {
      tocContainer.style.display = 'none';
      return;
    }

    const tocList = document.createElement('ul');

    headings.forEach((heading, index) => {
      // Generate ID if not present
      if (!heading.id) {
        heading.id = heading.textContent
          .toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/(^-|-$)/g, '') + '-' + index;
      }

      const li = document.createElement('li');
      li.className = `toc-${heading.tagName.toLowerCase()}`;

      const a = document.createElement('a');
      a.href = `#${heading.id}`;
      a.textContent = heading.textContent;

      li.appendChild(a);
      tocList.appendChild(li);
    });

    tocContainer.appendChild(tocList);
  }

  // Highlight current section in TOC based on scroll position
  function initTocHighlight() {
    const tocLinks = document.querySelectorAll('.toc a');
    if (tocLinks.length === 0) return;

    const headings = [];
    tocLinks.forEach(link => {
      const id = link.getAttribute('href').slice(1);
      const heading = document.getElementById(id);
      if (heading) headings.push({ id, element: heading, link });
    });

    function updateTocHighlight() {
      const navHeight = document.querySelector('.main-nav')?.offsetHeight || 0;
      const scrollPosition = window.scrollY + navHeight + 100;

      let currentHeading = headings[0];

      for (const heading of headings) {
        if (heading.element.offsetTop <= scrollPosition) {
          currentHeading = heading;
        }
      }

      tocLinks.forEach(link => link.classList.remove('active'));
      if (currentHeading) {
        currentHeading.link.classList.add('active');
      }
    }

    window.addEventListener('scroll', updateTocHighlight, { passive: true });
    updateTocHighlight();
  }

  // Initialize all features when DOM is ready
  function init() {
    initMobileNav();
    initSmoothScroll();
    initCodeCopy();
    initTableOfContents();
    initTocHighlight();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
