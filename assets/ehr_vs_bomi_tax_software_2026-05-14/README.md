# Bomi EHR vs Expert Billing Team Asset Folder

This folder is reserved for the pooled-state EHR-vs-Bomi creative test.

Target creative:

- Square: `ehr-vs-bomi-square-1080x1080.png`
- Landscape: `ehr-vs-bomi-landscape-1200x628.png`
- Google fallback portrait derivative: `ehr-vs-bomi-portrait-padded-1080x1920.png`
- Metadata: `moda_metadata.json`
- Meta handoff: `INFO.md`
- Meta activation readback: `meta_activation_readback.json`
- Google creation readback: `google_ads_readback.json`
- Google activation readback: `google_ads_activation_readback.json`

Generation command used:

```sh
python3 scripts/moda_generate_ehr_vs_bomi_assets.py
```

To conserve Moda credits, this run used one `lite` Moda square generation and
created the landscape and portrait formats locally from the approved square
asset.

Moda output:

- Task: `task_419RMBQN1T9ZCVPPW8F3KNGWEF`
- Canvas: `cvs_3KGFAVNS0Y98V9NKPD5V3VZJ1P`
- Brand kit: `bk_0PHT577BFH8E9VV0M9QYNM1M24`
- Generation mode: `single_moda_square_with_local_derivatives`
- Credits remaining after generation: `1290`

Platform objects:

- Meta campaign: `120248005997630170`
- Meta ad set: `120248006000710170`
- Meta creative: `998947609178695`
- Meta ad: `120248006007810170`
- Google Demand Gen campaign: `23851846966`
- Google Demand Gen budget: `15572267732`
- Google Demand Gen ad group: `197222331835`
- Google Demand Gen ad: `808795849849`

Current state after 2026-05-14 user approval:

- Meta/Facebook Feed is active at `$20/day`.
- Google Demand Gen is active at `$20/day`.

Validation and creation commands:

```sh
/Users/dax/.cache/bomi-ads-venv/bin/python scripts/meta_create_ehr_vs_bomi_pooled.py --apply
python3 scripts/google_ads_create_ehr_vs_bomi_demand_gen.py
python3 scripts/google_ads_create_ehr_vs_bomi_demand_gen.py --apply
```
