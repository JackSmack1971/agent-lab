# Agent Lab Phase 2 Wireframes: Progressive Visual Hierarchy

## Overview

These wireframes illustrate the implementation of progressive visual hierarchy and design system for Agent Lab. Each screen shows how the new design tokens, spacing grid, and component consistency create a more polished and accessible interface.

## Design System Application

### Visual Hierarchy Principles Applied
- **Content Grouping**: Related elements grouped with subtle borders and shadows
- **Information Density**: Optimized spacing creates clear scanning paths
- **Progressive Disclosure**: Complex options revealed contextually
- **Consistent Components**: All buttons, inputs, and cards follow unified styling

### Responsive Breakpoints
- **Mobile (320px)**: Single column, stacked layout
- **Tablet (768px)**: Two-column layout with adjusted proportions
- **Desktop (1024px+)**: Multi-column layout maximizing horizontal space

---

## Chat Tab Wireframes

### Desktop Layout (1024px+)
```
┌─────────────────────────────────────────────────────────────┐
│ Agent Lab - AI Testing Platform                           ≡ │
├─────────────────────────────────────────────────────────────┤
│ ┌─ Chat ─────────────────┐ ┌─ Message Input ──────────────┐ │
│ │                        │ │                              │ │
│ │ [Chat History]         │ │ ┌─────────────────────────┐  │ │
│ │                        │ │ │Message input area       │  │ │
│ │ User: Hello AI         │ │ │with placeholder text... │  │ │
│ │                        │ │ └─────────────────────────┘  │ │
│ │ Assistant: Hi there!   │ │                              │ │
│ │ How can I help?        │ │ ┌─────┐ ┌──────┐             │ │
│ │                        │ │ │Send │ │Stop  │             │ │
│ │ [More messages...]     │ │ └─────┘ └──────┘             │ │
│ │                        │ │                              │ │
│ └────────────────────────┘ └──────────────────────────────┘ │
│                                                             │
│ ┌─ Experiment Tagging ─────────────────────────────────────┐ │
│ │ ┌─────────────────┐ ┌─────────────┐ ┌──────────────────┐ │ │
│ │ │Experiment ID    │ │Task Type    │ │Run Notes         │ │ │
│ │ │[input field]    │ │[dropdown]   │ │[textarea]        │ │ │
│ │ └─────────────────┘ └─────────────┘ └──────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Key Improvements:**
- **Card-based Layout**: Each section contained in subtle shadow cards
- **Consistent Spacing**: 16px gaps between major sections, 8px within groups
- **Typography Hierarchy**: Clear heading sizes (25px, 20px, 16px)
- **Component Consistency**: All inputs follow same styling with proper focus states

### Mobile Layout (320px)
```
┌─────────────────────┐
│ Agent Lab         ≡ │
├─────────────────────┤
│                     │
│ [Chat History]      │
│                     │
│ User: Hello AI      │
│                     │
│ Asst: Hi there!     │
│ How can I help?     │
│                     │
│ [Scroll indicator]  │
│                     │
├─────────────────────┤
│ Message Input       │
│ ┌─────────────────┐ │
│ │Type message...  │ │
│ └─────────────────┘ │
│                     │
│ ┌─────┐ ┌──────┐   │
│ │Send │ │Stop  │   │
│ └─────┘ └──────┘   │
├─────────────────────┤
│ Experiment Tagging  │
│ [Collapsible]       │
│                     │
│ Experiment ID:      │
│ [input]             │
│                     │
│ Task Type:          │
│ [dropdown]          │
│                     │
│ Run Notes:          │
│ [textarea]          │
└─────────────────────┘
```

**Mobile Optimizations:**
- **Single Column**: All content stacks vertically
- **Touch Targets**: 44px minimum button height
- **Progressive Disclosure**: Experiment tagging collapsed by default
- **Readable Typography**: 16px minimum font size maintained

---

## Configuration Tab Wireframes

### Desktop Layout (1024px+)
```
┌─────────────────────────────────────────────────────────────┐
│ Agent Lab - Configuration                                 ≡ │
├─────────────────────────────────────────────────────────────┤
│ ┌─ Agent Configuration ────────────────────────────────────┐ │
│ │ ┌─────────────────────────────────────────────────────┐   │ │
│ │ │ Agent Name                                           │   │ │
│ │ │ ┌─────────────────────────────────────────────────┐ │   │ │
│ │ │ │[input field with validation]                   │ │   │ │
│ │ │ └─────────────────────────────────────────────────┘ │   │ │
│ │ │                                                     │   │ │
│ │ │ Model Selection                                     │   │ │
│ │ │ ┌─────────────────────────────────────────────────┐ │   │ │
│ │ │ │GPT-4 Turbo (OpenAI) ▼                          │ │   │ │
│ │ │ └─────────────────────────────────────────────────┘ │   │ │
│ │ │ Model catalog: Dynamic (fetched 14:32)             │   │ │
│ │ │ ┌────────────┐                                      │   │ │
│ │ │ │Refresh     │                                      │   │ │
│ │ │ └────────────┘                                      │   │ │
│ │ │                                                     │   │ │
│ │ │ System Prompt                                       │   │ │
│ │ │ ┌─────────────────────────────────────────────────┐ │   │ │
│ │ │ │You are a helpful assistant. [200 chars]         │ │   │ │
│ │ │ └─────────────────────────────────────────────────┘ │   │ │
│ │ │                                                     │   │ │
│ │ │ Parameters                                          │   │ │
│ │ │ ┌─────────────────┐ ┌─────────────────┐             │   │ │
│ │ │ │Temperature: 0.7 │ │Top-p: 1.0      │             │   │ │
│ │ │ │[slider]         │ │[slider]         │             │   │ │
│ │ │ └─────────────────┘ └─────────────────┘             │   │ │
│ │ │                                                     │   │ │
│ │ │ □ Enable Web Tool                                   │   │ │
│ │ │                                                     │   │ │
│ │ │ ┌────────────┐                                      │   │ │
│ │ │ │Build Agent │                                      │   │ │
│ │ │ └────────────┘                                      │   │ │
│ │ └─────────────────────────────────────────────────────┘   │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Model Information ───────────────────────────────────────┐ │
│ │ ┌─────────────────────────────────────────────────────┐   │ │
│ │ │ Web Tool: ON                                         │   │ │
│ │ │                                                     │   │ │
│ │ │ Status: Agent built successfully                    │   │ │
│ │ │                                                     │   │ │
│ │ │ Parameter Guidance                                  │   │ │
│ │ │ Temperature affects creativity                      │   │ │
│ │ │ Top-p controls diversity                            │   │ │
│ │ └─────────────────────────────────────────────────────┘   │ │
│ └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Visual Hierarchy Features:**
- **Clear Section Separation**: Cards with subtle shadows group related controls
- **Progressive Disclosure**: Parameter guidance appears contextually
- **Status Indicators**: Clear visual feedback for validation and build status
- **Consistent Spacing**: 24px between major sections, 16px between form groups

### Tablet Layout (768px)
```
┌─────────────────────┐
│ Agent Lab Config  ≡ │
├─────────────────────┤
│ Agent Configuration │
│                     │
│ Agent Name          │
│ ┌─────────────────┐ │
│ │[input]          │ │
│ └─────────────────┘ │
│                     │
│ Model Selection     │
│ ┌─────────────────┐ │
│ │GPT-4 ▼          │ │
│ └─────────────────┘ │
│ Dynamic (14:32)     │
│ [Refresh]           │
│                     │
│ System Prompt       │
│ ┌─────────────────┐ │
│ │[textarea]       │ │
│ └─────────────────┘ │
│                     │
│ Parameters          │
│ Temp: 0.7 [slider]  │
│ Top-p: 1.0 [slider] │
│                     │
│ □ Web Tool          │
│                     │
│ [Build Agent]       │
├─────────────────────┤
│ Model Information   │
│                     │
│ Web Tool: ON        │
│                     │
│ Status: Ready       │
│                     │
│ Parameter Tips      │
│ Temp: creativity    │
│ Top-p: diversity    │
└─────────────────────┘
```

**Tablet Adaptations:**
- **Two-Column Layout**: Configuration left, information right
- **Condensed Spacing**: Optimized for medium screens
- **Touch-Friendly**: Larger touch targets maintained

---

## Sessions Tab Wireframes

### Desktop Layout (1024px+)
```
┌─────────────────────────────────────────────────────────────┐
│ Agent Lab - Sessions                                      ≡ │
├─────────────────────────────────────────────────────────────┤
│ ┌─ Session Management ─────────────────────────────────────┐ │
│ │ ┌─────────────────────────────────────────────────────┐   │ │
│ │ │ Session Name                                         │   │ │
│ │ │ ┌─────────────────────────────────────────────────┐ │   │ │
│ │ │ │experiment-gpt4-vs-claude                      │ │   │ │
│ │ │ └─────────────────────────────────────────────────┘ │   │ │
│ │ │                                                     │   │ │
│ │ │ ┌────────┐ ┌────────┐ ┌────────┐                   │   │ │
│ │ │ │ Save   │ │ Load   │ │ New    │                   │   │ │
│ │ │ └────────┘ └────────┘ └────────┘                   │   │ │
│ │ │                                                     │   │ │
│ │ │ Status: Session loaded successfully                │   │ │
│ │ └─────────────────────────────────────────────────────┘   │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Session Details ─────────────────────────────────────────┐ │
│ │ ┌─ Transcript Preview ─┐ ┌─ Session Metadata ──────────┐   │ │
│ │ │                      │ │                             │   │ │
│ │ │ [Chat history]       │ │ ID: abc-123-def            │   │ │
│ │ │                      │ │ Created: 2025-01-15        │   │ │
│ │ │ User: Hello          │ │ Agent: Test Agent          │   │ │
│ │ │                      │ │ Model: GPT-4 Turbo         │   │ │
│ │ │ Asst: Hi there!      │ │ Notes: Performance test    │   │ │
│ │ │                      │ │                             │   │ │
│ │ │ [More messages...]   │ │ Parameters:                │   │ │
│ │ │                      │ │ Temp: 0.7, Top-p: 1.0      │   │ │
│ │ └──────────────────────┘ └─────────────────────────────┘   │ │
│ └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Session Management Features:**
- **Clear Status Indicators**: Visual feedback for all operations
- **Organized Information**: Metadata clearly separated from content
- **Consistent Actions**: All buttons follow same styling patterns
- **Progressive Loading**: Content loads in logical order

---

## Analytics Tab Wireframes

### Desktop Layout (1024px+)
```
┌─────────────────────────────────────────────────────────────┐
│ Agent Lab - Analytics                                     ≡ │
├─────────────────────────────────────────────────────────────┤
│ ┌─ Run Statistics ─────────────────────────────────────────┐ │
│ │ ┌─────────────────────────────────────────────────────┐   │ │
│ │ │ Total Runs: 42                                       │   │ │
│ │ │ Success Rate: 95%                                    │   │ │
│ │ │ Avg Response Time: 2.3s                              │   │ │
│ │ │ Total Cost: $1.24                                    │   │ │
│ │ │                                                     │   │ │
│ │ │ ┌─────────────────┐                                  │   │ │
│ │ │ │Download CSV     │                                  │   │ │
│ │ │ └─────────────────┘                                  │   │ │
│ │ └─────────────────────────────────────────────────────┘   │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Visualizations ──────────────────────────────────────────┐ │
│ │ ┌─────────────────────────────────────────────────────┐   │ │
│ │ │ [Chart Area]                                         │   │ │
│ │ │                                                     │   │ │
│ │ │ Model Performance Comparison                        │   │ │
│ │ │ ████████ GPT-4 Turbo                                │   │ │
│ │ │ ██████ Claude 3                                      │   │ │
│ │ │ ████ Gemini 1.5                                      │   │ │
│ │ │                                                     │   │ │
│ │ │ Response Time by Model                              │   │ │
│ │ │ ▓▓▓▓▓▓▓▓ GPT-4: 1.8s                               │   │ │
│ │ │ ▓▓▓▓▓▓ Claude: 2.1s                                 │   │ │
│ │ │ ▓▓▓▓ Gemini: 2.7s                                   │   │ │
│ │ └─────────────────────────────────────────────────────┘   │ │
│ └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

**Analytics Features:**
- **Data Hierarchy**: Key metrics prominently displayed
- **Visual Consistency**: Charts follow design system colors
- **Actionable Layout**: Download button clearly positioned
- **Progressive Enhancement**: Basic stats always visible, charts load secondarily

---

## User Journey Maps

### Primary User Journey: AI Researcher Testing Models

1. **Discovery** → Clean, professional interface builds trust
2. **Configuration** → Progressive disclosure reduces cognitive load
3. **Experimentation** → Consistent patterns enable efficient workflow
4. **Analysis** → Clear data presentation supports decision making
5. **Iteration** → Session management preserves work context

### Secondary Journey: QA Tester Validating Scenarios

1. **Setup** → Accessible controls ensure all users can configure
2. **Testing** → Reliable patterns support repetitive tasks
3. **Documentation** → Session saving captures test evidence
4. **Reporting** → Analytics provide validation metrics

### Edge Case Journey: Mobile User on Tablet

1. **Responsive Adaptation** → Layout reflows appropriately
2. **Touch Optimization** → All controls meet accessibility standards
3. **Content Prioritization** → Essential features remain accessible
4. **Progressive Enhancement** → Advanced features available when space permits

---

## Accessibility Features Illustrated

### Focus Management
- **Visible Focus Rings**: 3px blue outline on all interactive elements
- **Logical Tab Order**: Matches visual layout reading order
- **Skip Links**: Keyboard users can jump to main content areas

### Screen Reader Support
- **Semantic Landmarks**: Header, navigation, main, complementary roles
- **ARIA Labels**: Descriptive labels for complex widgets
- **Live Regions**: Status updates announced automatically

### Color & Contrast
- **High Contrast Text**: All text meets WCAG AA standards
- **Semantic Colors**: Status conveyed through multiple channels
- **Focus Indicators**: High contrast focus rings always visible

### Touch & Mobile
- **44px Touch Targets**: All buttons and inputs meet minimum size
- **Gesture Support**: Swipe gestures for navigation where appropriate
- **Responsive Text**: Scales appropriately across devices

---

## Implementation Notes

### CSS Architecture
- **Design Tokens**: All values stored as CSS custom properties
- **Component Classes**: Consistent styling across instances
- **Utility Classes**: Reusable spacing, typography, color utilities
- **State Management**: Consistent hover, focus, active states

### Performance Considerations
- **Critical CSS**: Above-the-fold styles inlined
- **Lazy Loading**: Component styles loaded as needed
- **Minification**: Production CSS compressed
- **Caching**: Static assets cached aggressively

### Browser Support
- **Modern Browsers**: Full feature support
- **Progressive Enhancement**: Core functionality without CSS
- **Graceful Degradation**: Usable experience on older browsers

These wireframes demonstrate how the design system creates a cohesive, accessible, and professional interface that scales across devices and use cases.