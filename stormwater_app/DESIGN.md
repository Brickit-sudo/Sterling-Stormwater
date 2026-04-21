# Design System Inspired by Sterling & MongoDB

## 1. Visual Theme & Atmosphere

[cite_start]This design system is a deep-forest-meets-infrastructure experience — rooted in the darkest teal-black (`#001e2b`) that evokes both the density of a database and the reliability of structural maintenance[cite: 32, 80]. [cite_start]Against this near-black canvas, a **Vivid Maintenance Green** (`#27AD3D`) serves as the brand accent — a color that feels organic, professional, and grounded in environmental stewardship[cite: 30, 60]. Unlike high-energy neon, this green represents growth, stability, and the precision of field-service engineering.

The typography system is architecturally ambitious: MongoDB Value Serif for massive hero headlines (96px) creates an editorial, authoritative presence. Euclid Circular A handles the heavy lifting of body and UI text, while Source Code Pro serves as the code and label font with distinctive uppercase treatments. This creates a hierarchy spanning editorial elegance → geometric professionalism → engineering precision.

What makes this system distinctive is its dual-mode design: a dark hero/feature section world (`#001e2b` with vivid green accents) and a light content world (white with teal-gray borders `#b8c4c2`). The transition between these modes creates dramatic contrast. Shadows use teal-tinted dark tones (`rgba(0, 30, 43, 0.12)`) to maintain the forest-dark atmosphere across all surfaces.

**Key Characteristics:**
- [cite_start]Deep teal-black backgrounds (`#001e2b`) — forest-dark, not space-dark [cite: 32]
- [cite_start]**Vivid Maintenance Green** (`#27AD3D`) as the singular brand accent — professional and organic [cite: 32, 57]
- MongoDB Value Serif for hero headlines — editorial authority at tech scale
- Euclid Circular A for body with weight 300 (light) as a distinctive body weight
- Source Code Pro with wide uppercase letter-spacing (1px–3px) for technical labels
- Teal-tinted shadows: `rgba(0, 30, 43, 0.12)` — shadows carry the forest color
- Dual-mode: dark teal hero sections + light white content sections
- Pill buttons (100px radius) with dark green borders (`#1E822E`)
- Link Blue (`#006cfa`) and hover transition to `#3860be`

## 2. Color Palette & Roles

### Primary Brand
- [cite_start]**Forest Black** (`#001e2b`): Primary dark background — the deepest teal-black [cite: 80]
- [cite_start]**Vivid Maintenance Green** (`#27AD3D`): Primary brand accent — used for logo accents, highlights, and primary text links [cite: 30, 60]
- **Service Green** (`#1E822E`): Button borders, functional UI states — a darker, high-contrast variant of the brand green

### Interactive
- **Action Blue** (`#006cfa`): Secondary accent — links, interactive highlights
- **Hover Blue** (`#3860be`): All link hover states transition to this blue
- **Teal Active** (`#1eaedb`): Button hover background — bright teal

### Neutral Scale
- **Deep Teal** (`#1c2d38`): Dark button backgrounds, secondary dark surfaces
- **Teal Gray** (`#3d4f58`): Dark borders on dark surfaces
- **Dark Slate** (`#21313c`): Dark link text variant
- **Cool Gray** (`#5c6c75`): Muted text on dark, secondary button text
- **Silver Teal** (`#b8c4c2`): Borders on light surfaces, dividers
- **Light Input** (`#e8edeb`): Input text on dark surfaces
- **Pure White** (`#ffffff`): Light section background, button text on dark
- **Black** (`#000000`): Text on light surfaces, darkest elements

### Shadows
- **Forest Shadow** (`rgba(0, 30, 43, 0.12) 0px 26px 44px, rgba(0, 0, 0, 0.13) 0px 7px 13px`): Primary card elevation — teal-tinted
- **Standard Shadow** (`rgba(0, 0, 0, 0.15) 0px 3px 20px`): General elevation
- **Subtle Shadow** (`rgba(0, 0, 0, 0.1) 0px 2px 4px`): Light card lift

## 3. Typography Rules

### Font Families
- **Display Serif**: `MongoDB Value Serif` — editorial hero headlines
- **Body / UI**: `Euclid Circular A` — geometric sans-serif workhorse
- **Code / Labels**: `Source Code Pro` — monospace with uppercase label treatments

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Display Hero | MongoDB Value Serif | 96px (6.00rem) | 400 | 1.20 | normal | Serif authority |
| Body | Euclid Circular A | 18px (1.13rem) | 400 | 1.33 | normal | Standard body |
| UI Label | Source Code Pro | 14px (0.88rem) | 400–500 | 1.14 | 1px–2px | Brand technical voice |

## 4. Component Stylings

### Buttons

**Primary Maintenance Green (Dark Surface)**
- [cite_start]Background: `#27AD3D` [cite: 32, 57]
- Text: `#ffffff`
- Radius: 100px (pill)
- Border: `1px solid #1E822E`
- Hover: scale 1.05, background darkened
- Active: scale 0.95

**Dark Teal Button**
- Background: `#1c2d38`
- Text: `#5c6c75`
- Radius: 100px (pill)
- Border: `1px solid #3d4f58`
- Hover: background `#1eaedb`, text white, translateX(5px)

### Distinctive Components

**Maintenance Accent Underlines**
- [cite_start]`0px 2px 2px 0px solid #27AD3D` — bottom + right border creating accent underlines [cite: 32, 80]
- [cite_start]Used on feature headings and highlighted text to mirror the bars in the brand logo [cite: 30, 60]

**Source Code Label System**
- 14px uppercase Source Code Pro with 1px–2px letter-spacing
- Used as section category markers above headings
- [cite_start]Represents the "field data" aesthetic of inspection reporting [cite: 1, 35]

## 5. Layout Principles

### Spacing System
- Base unit: 8px
- [cite_start]Grid: Full-width dark sections for high-impact brand areas, white sections for dense technical data [cite: 3, 37, 61]

### Whitespace Philosophy
- **Generous dark sections**: Dark hero areas use extra vertical padding to allow the `#001e2b` forest background to emphasize the `#27AD3D` green accents.

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Forest (Level 4) | `rgba(0,30,43,0.12) 0px 26px 44px` | Hero cards — teal-tinted |

## 7. Do's and Don'ts

### Do
- [cite_start]Use `#001e2b` (forest-black) for dark sections [cite: 80]
- [cite_start]Apply **Maintenance Green** (`#27AD3D`) for logo bars, tagline text, and primary CTAs [cite: 30, 32]
- [cite_start]Use the green accent underlines to highlight "Service Findings" or "Key Recommendations" [cite: 9, 43, 67]
- Maintain the dark/light section duality to represent the transition from high-level "Environmental Insight" to detailed "Maintenance Data."

### Don't
- [cite_start]Don't use neon/electric greens — stay within the mid-range organic green of the brand identity [cite: 32, 57]
- Don't use pure black — always lean into the teal-forest tones
- [cite_start]Don't apply the green to large background areas; it is an accent color meant for bars, borders, and text labels [cite: 30, 60]

## 9. Agent Prompt Guide

### Quick Color Reference
- Dark background: Forest Black (`#001e2b`)
- Brand accent: **Maintenance Green** (`#27AD3D`)
- Functional green: Service Green (`#1E822E`)
- Link blue: Action Blue (`#006cfa`)

### Example Component Prompts
- "Create a hero on forest-black (#001e2b) background. Headline at 96px white text with 'Environmental Integrity' highlighted with a bottom-border in Maintenance Green (#27AD3D). Green pill CTA (#27AD3D, 100px radius)."
- "Design a technical data label: Source Code Pro 14px, uppercase, 2px letter-spacing, #27AD3D color on dark background."