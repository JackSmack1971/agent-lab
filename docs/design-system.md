# Agent Lab Design System

## Overview

This document defines the comprehensive design system for Agent Lab, implementing progressive visual hierarchy and consistent styling across all components. The system ensures WCAG 2.1 AA compliance while providing a polished, professional interface.

## Design Principles

### Progressive Visual Hierarchy
- **Clear Content Grouping**: Related elements are visually grouped with subtle shadows and borders
- **Information Density**: Content is organized to optimize scanning and reading flow
- **Consistent Spacing**: Uniform spacing creates rhythm and improves comprehension
- **Semantic Color Usage**: Colors convey meaning and state information

### Accessibility-First Approach
- **WCAG 2.1 AA Compliance**: All contrast ratios meet or exceed standards
- **Semantic HTML**: Proper use of headings, landmarks, and ARIA attributes
- **Keyboard Navigation**: Full functionality accessible via keyboard
- **Screen Reader Support**: Comprehensive screen reader compatibility

### Mobile-First Responsive Design
- **Breakpoint Strategy**: 320px (mobile), 768px (tablet), 1024px (desktop)
- **Touch Targets**: Minimum 44px touch targets for mobile devices
- **Content Adaptation**: Layouts adapt gracefully across screen sizes
- **No Horizontal Scroll**: All content fits within viewport width

## Design Tokens

### Typography Scale

```css
:root {
  /* Font Sizes */
  --text-xs: 12px;    /* Small labels, captions */
  --text-sm: 16px;    /* Body text, inputs */
  --text-base: 20px;  /* Headings, emphasis */
  --text-lg: 25px;    /* Section headings */
  --text-xl: 31px;    /* Page headings */
  --text-2xl: 39px;   /* Hero headings */

  /* Line Heights (1.5x ratio) */
  --leading-xs: 18px;
  --leading-sm: 24px;
  --leading-base: 30px;
  --leading-lg: 37.5px;
  --leading-xl: 46.5px;
  --leading-2xl: 58.5px;

  /* Font Weights */
  --font-light: 400;
  --font-normal: 500;
  --font-semibold: 600;
  --font-bold: 700;

  /* Font Family */
  --font-primary: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'SF Mono', Monaco, 'Cascadia Code', monospace;
}
```

### Spacing Grid (4px Base)

```css
:root {
  /* Spacing Scale */
  --space-1: 4px;    /* Minimal gaps */
  --space-2: 8px;    /* Small gaps, padding */
  --space-3: 16px;   /* Component padding */
  --space-4: 24px;   /* Section spacing */
  --space-5: 32px;   /* Large gaps */
  --space-6: 48px;   /* Major section breaks */
  --space-7: 64px;   /* Page-level spacing */

  /* Layout Spacing */
  --container-padding: var(--space-4);
  --section-margin: var(--space-6);
  --component-gap: var(--space-3);
}
```

### Color System

#### Semantic Colors
```css
:root {
  /* Primary Colors */
  --color-primary: #0066cc;
  --color-primary-hover: #0052a3;
  --color-primary-active: #004080;

  /* Semantic Colors */
  --color-success: #28a745;
  --color-warning: #ffc107;
  --color-error: #dc3545;
  --color-info: #17a2b8;

  /* Neutral Colors */
  --color-text-primary: #212529;
  --color-text-secondary: #6c757d;
  --color-text-muted: #868e96;

  /* Background Colors */
  --color-bg-primary: #ffffff;
  --color-bg-secondary: #f8f9fa;
  --color-bg-tertiary: #e9ecef;

  /* Border Colors */
  --color-border-light: #dee2e6;
  --color-border-medium: #ced4da;
  --color-border-dark: #adb5bd;

  /* Shadow Colors */
  --color-shadow-light: rgba(0, 0, 0, 0.1);
  --color-shadow-medium: rgba(0, 0, 0, 0.15);
  --color-shadow-dark: rgba(0, 0, 0, 0.25);
}
```

#### Accessibility Color Variants
```css
:root {
  /* High Contrast Variants */
  --color-text-primary-hc: #000000;
  --color-bg-primary-hc: #ffffff;

  /* Focus Indicators */
  --color-focus: #0066cc;
  --color-focus-ring: rgba(0, 102, 204, 0.3);

  /* Interactive States */
  --color-hover-bg: rgba(0, 102, 204, 0.1);
  --color-active-bg: rgba(0, 102, 204, 0.2);
}
```

### Border Radius & Shadows

```css
:root {
  /* Border Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;

  /* Box Shadows */
  --shadow-sm: 0 1px 3px var(--color-shadow-light);
  --shadow-md: 0 4px 6px var(--color-shadow-medium);
  --shadow-lg: 0 10px 15px var(--color-shadow-dark);
  --shadow-xl: 0 20px 25px var(--color-shadow-dark);
}
```

## Component Patterns

### Buttons

#### Primary Button
```css
.btn-primary {
  background: var(--color-primary);
  color: white;
  border: 2px solid var(--color-primary);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  line-height: var(--leading-sm);
  min-height: 44px;
  transition: all 0.2s ease;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-primary:active {
  background: var(--color-primary-active);
  transform: translateY(0);
}

.btn-primary:focus {
  outline: none;
  box-shadow: 0 0 0 3px var(--color-focus-ring);
}
```

#### Secondary Button
```css
.btn-secondary {
  background: transparent;
  color: var(--color-primary);
  border: 2px solid var(--color-primary);
  /* ... same dimensions and focus styles as primary */
}
```

### Form Inputs

#### Text Input
```css
.form-input {
  width: 100%;
  padding: var(--space-2) var(--space-3);
  border: 2px solid var(--color-border-medium);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  line-height: var(--leading-sm);
  background: var(--color-bg-primary);
  transition: border-color 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-focus-ring);
}

.form-input:invalid {
  border-color: var(--color-error);
}
```

### Cards & Panels

#### Content Card
```css
.card {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-4);
  margin-bottom: var(--space-4);
}

.card-header {
  margin-bottom: var(--space-3);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border-light);
}
```

### Typography Classes

#### Headings
```css
.heading-1 { font-size: var(--text-2xl); font-weight: var(--font-bold); line-height: var(--leading-2xl); }
.heading-2 { font-size: var(--text-xl); font-weight: var(--font-bold); line-height: var(--leading-xl); }
.heading-3 { font-size: var(--text-lg); font-weight: var(--font-semibold); line-height: var(--leading-lg); }
.heading-4 { font-size: var(--text-base); font-weight: var(--font-semibold); line-height: var(--leading-base); }
```

#### Body Text
```css
.text-body { font-size: var(--text-sm); line-height: var(--leading-sm); color: var(--color-text-primary); }
.text-secondary { color: var(--color-text-secondary); }
.text-muted { color: var(--color-text-muted); }
```

## Responsive Design System

### Breakpoints
```css
/* Mobile First */
.container { width: 100%; padding: 0 var(--space-3); }

/* Tablet */
@media (min-width: 768px) {
  .container { max-width: 720px; margin: 0 auto; padding: 0 var(--space-4); }
}

/* Desktop */
@media (min-width: 1024px) {
  .container { max-width: 960px; }
}

/* Large Desktop */
@media (min-width: 1200px) {
  .container { max-width: 1140px; }
}
```

### Grid System
```css
.grid {
  display: grid;
  gap: var(--space-4);
}

.grid-cols-1 { grid-template-columns: 1fr; }
.grid-cols-2 { grid-template-columns: repeat(2, 1fr); }
.grid-cols-3 { grid-template-columns: repeat(3, 1fr); }

/* Responsive grids */
@media (max-width: 767px) {
  .grid-cols-2, .grid-cols-3 { grid-template-columns: 1fr; }
}
```

## Accessibility Guidelines

### Color Contrast Requirements
- **Normal Text**: 4.5:1 minimum contrast ratio
- **Large Text**: 3:1 minimum contrast ratio (18pt+ or 14pt+ bold)
- **Interactive Elements**: 3:1 minimum contrast ratio
- **Focus Indicators**: 3:1 contrast against adjacent colors

### Focus Management
- **Visible Focus**: 2px solid focus rings with 3:1 contrast
- **Logical Order**: Tab order matches visual layout
- **Keyboard Navigation**: All functionality accessible via keyboard
- **Focus Trapping**: Modal dialogs trap focus appropriately

### Semantic HTML
- **Landmarks**: Use header, nav, main, aside, footer
- **Headings**: Proper heading hierarchy (h1 → h2 → h3)
- **Lists**: Use ol/ul for list content
- **Buttons vs Links**: Use correct semantic elements

### Screen Reader Support
- **ARIA Labels**: Descriptive labels for complex widgets
- **Live Regions**: Announce dynamic content changes
- **Hidden Content**: Use sr-only class for screen reader only content
- **Alt Text**: Meaningful alternative text for images

## Implementation Guidelines

### CSS Architecture
1. **Design Tokens First**: All values derive from CSS custom properties
2. **Component Classes**: Specific styling for each component type
3. **Utility Classes**: Reusable styling utilities
4. **State Classes**: Consistent hover, focus, active states

### Naming Convention
- **Components**: `.component-name`
- **Modifiers**: `.component-name--modifier`
- **Utilities**: `.u-utility-name`
- **States**: `.is-state-name`

### Performance Considerations
- **Critical CSS**: Inline above-the-fold styles
- **Lazy Loading**: Load component styles as needed
- **Minification**: Compress CSS for production
- **Caching**: Cache design tokens and utilities

## Quality Assurance

### Automated Testing
- **Contrast Checking**: Automated contrast ratio validation
- **Color Accessibility**: Color blindness simulation testing
- **Responsive Testing**: Viewport size validation
- **Component Consistency**: Visual regression testing

### Manual Testing Checklist
- [ ] All text meets contrast requirements
- [ ] Focus indicators are visible and consistent
- [ ] Keyboard navigation works throughout
- [ ] Screen readers announce content properly
- [ ] Touch targets meet minimum size requirements
- [ ] No horizontal scrolling on mobile devices
- [ ] Color coding is not the only way information is conveyed

## Browser Support

### Supported Browsers
- **Chrome**: Latest 2 versions
- **Firefox**: Latest 2 versions
- **Safari**: Latest 2 versions
- **Edge**: Latest 2 versions

### Progressive Enhancement
- **Core Functionality**: Works without CSS
- **Enhanced Experience**: Requires modern CSS support
- **Graceful Degradation**: Falls back to usable state

## Maintenance & Updates

### Version Control
- **Semantic Versioning**: Major.Minor.Patch
- **Breaking Changes**: Major version bumps
- **Deprecation Notices**: Advance warning for removed features

### Documentation Updates
- **Component Inventory**: Maintain list of all components
- **Usage Guidelines**: Document proper component usage
- **Migration Guides**: Help with breaking changes

This design system provides a solid foundation for consistent, accessible, and maintainable UI components across Agent Lab.