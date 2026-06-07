# EvE Crafting Glorified

> ## 🚧 WORK IN PROGRESS — EARLY PROTOTYPE 🚧
> This is an **unfinished, experimental prototype**, not a finished tool. Code,
> data formats, and approach are all in flux and may change or break at any time.
> Published for transparency/portfolio purposes — **not ready for general use.**

A personal project exploring **constraint solving applied to EVE Online's
crafting / manufacturing system** — figuring out optimal ways to produce
"Glorified" items given available materials, blueprints, and constraints.

## Current state

Right now this is mostly the **data-ingestion groundwork** for the optimizer:

- `lookup-parser.py` — parses raw in-game blueprint/material dumps
  (`mat-dump.txt`) into structured rows (`parsed_blueprints.csv`).
- `paste-processor.py` — processes pasted game data into usable form.
- Sample data: `mat-dump.txt`, `stock-paste.txt`, `parsed_blueprints.csv`,
  `rolling-partners.csv`.

The **constraint-solving optimizer itself** (the interesting part) is the next
step and not implemented yet.

## Goal / vision

Turn the parsed crafting data into a solver that, given a target item and an
inventory of materials/blueprints, computes optimal production plans under
constraints (cost, available inputs, profitability). Longer term this may be
integrated into my larger EVE tool (EVE IPH Flint Edition), but for now it
stays a separate, lightweight Python prototype.

## Status

Prototype · work in progress · actively want to finish this eventually.
