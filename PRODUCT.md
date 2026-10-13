# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Static single-file HTML + CSS, Three.js loaded from a pinned CDN. No build step; opens by double-click. (Confirmed by the user.)

## Users

The repo owner, a demand planner for a US beauty scope (fragrance and color) working in O9, and their planning team. They open the page on a laptop to look at one SKU with its planning numbers beside it. (Confirmed: internal planning demo.)

## Product Purpose

Internal demo that pairs a 3D model of a fragrance SKU with its planning figures (forecast, sales, stock, coverage). All figures on the page are simulated; nothing comes from O9 yet. (Confirmed.)

## Operating Context

Read on desktop first, also checked on phone. Scroll drives the story: the bottle sits centered and turns as the reader scrolls, while figures appear around it. (Confirmed: centered, rotating bottle.)

## Brand Commitments

Visual world is fixed by DESIGN.md in the repo root (dark void, single violet action color, amber highlights, ultra-light body). The user explicitly asked for the 3D model on the page, which overrides DESIGN.md's "no 3D renders in the hero" rule for this surface.

## Evidence on Hand

- `model.png`: product reference photo of the bottle (front view only).
- `CONTEXTO-DATOS.md`: describes the planning data domain. No real numbers are used on this page.

## Product Principles

- Simulated numbers are labeled as simulated on the page.
- The page is internal; it does not present itself as the fragrance brand's own site.
