/**
 * Terry-Form MCP Documentation - Main JavaScript
 * Handles theme toggle, navigation, code copying, TOC, tabs, and scroll spy
 */

(function() {
  'use strict';

  // Theme toggle with localStorage persistence
  function initThemeToggle() {
    const toggle = document.querySelector('.theme-toggle');
    if (!toggle) return;

    const saved = localStorage.getItem('terry-theme');
    if (saved === 'dark') {
      document.documentElement.classList.add('dark-theme');
      document.documentElement.classList.remove('light-theme');
    } else if (saved === 'light') {
      document.documentElement.classList.add('light-theme');
      document.documentElement.classList.remove('dark-theme');
    }

    toggle.addEventListener('click', function() {
      const isDark = document.documentElement.classList.contains('dark-theme');
      const isLight = document.documentElement.classList.contains('light-theme');

      if (isDark) {
        document.documentElement.classList.remove('dark-theme');
        document.documentElement.classList.add('light-theme');
        localStorage.setItem('terry-theme', 'light');
      } else if (isLight) {
        document.documentElement.classList.remove('light-theme');
        document.documentElement.classList.add('dark-theme');
        localStorage.setItem('terry-theme', 'dark');
      } else {
        // No explicit class - check system preference
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        if (prefersDark) {
          document.documentElement.classList.add('light-theme');
          localStorage.setItem('terry-theme', 'light');
        } else {
          document.documentElement.classList.add('dark-theme');
          localStorage.setItem('terry-theme', 'dark');
        }
      }
    });
  }

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

    document.addEventListener('click', function(event) {
      if (!event.target.closest('.nav-container')) {
        navMenu.classList.remove('active');
        navToggle.classList.remove('active');
        navToggle.setAttribute('aria-expanded', 'false');
      }
    });

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
          window.scrollTo({ top: targetPosition, behavior: 'smooth' });
          history.pushState(null, null, targetId);
        }
      });
    });
  }

  // Copy code button for code blocks
  function initCodeCopy() {
    document.querySelectorAll('pre code').forEach(block => {
      const pre = block.parentElement;
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
          setTimeout(() => { button.innerHTML = 'Copy'; button.classList.remove('copied'); }, 2000);
        } catch (err) {
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
            setTimeout(() => { button.innerHTML = 'Copy'; button.classList.remove('copied'); }, 2000);
          } catch (e) { /* silent fail */ }
          document.body.removeChild(textArea);
        }
      });
    });
  }

  // Table of Contents generation
  function initTableOfContents() {
    const tocContainer = document.querySelector('.toc');
    if (!tocContainer) return;

    const contentArea = document.querySelector('.guide-body, .tutorial-content, .api-content, .page-content, .main-content');
    if (!contentArea) return;

    const headings = contentArea.querySelectorAll('h2, h3');
    if (headings.length === 0) { tocContainer.style.display = 'none'; return; }

    const tocList = document.createElement('ul');
    headings.forEach((heading, index) => {
      if (!heading.id) {
        heading.id = heading.textContent.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') + '-' + index;
      }
      const li = document.createElement('li');
      li.className = 'toc-' + heading.tagName.toLowerCase();
      const a = document.createElement('a');
      a.href = '#' + heading.id;
      a.textContent = heading.textContent;
      li.appendChild(a);
      tocList.appendChild(li);
    });
    tocContainer.appendChild(tocList);
  }

  // IntersectionObserver-based TOC scroll spy
  function initTocScrollSpy() {
    const tocLinks = document.querySelectorAll('.toc a');
    if (tocLinks.length === 0) return;

    const headingMap = new Map();
    tocLinks.forEach(link => {
      const id = link.getAttribute('href').slice(1);
      const heading = document.getElementById(id);
      if (heading) headingMap.set(heading, link);
    });

    if (headingMap.size === 0) return;

    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          tocLinks.forEach(l => l.classList.remove('active'));
          const link = headingMap.get(entry.target);
          if (link) link.classList.add('active');
        }
      });
    }, {
      rootMargin: '-80px 0px -70% 0px',
      threshold: 0
    });

    headingMap.forEach((link, heading) => observer.observe(heading));
  }

  // Tab component
  function initTabs() {
    document.querySelectorAll('.tab-group').forEach(group => {
      const buttons = group.querySelectorAll('.tab-btn');
      const panels = group.querySelectorAll('.tab-panel');

      buttons.forEach(btn => {
        btn.addEventListener('click', () => {
          const target = btn.dataset.tab;
          buttons.forEach(b => b.classList.remove('active'));
          panels.forEach(p => p.classList.remove('active'));
          btn.classList.add('active');
          const panel = group.querySelector('[data-tab-panel="' + target + '"]');
          if (panel) panel.classList.add('active');
        });
      });
    });
  }

  // Initialize
  function init() {
    initThemeToggle();
    initMobileNav();
    initSmoothScroll();
    initCodeCopy();
    initTableOfContents();
    initTocScrollSpy();
    initTabs();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
