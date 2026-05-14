# Bomi Own Your Business Asset Folder

This folder contains the pooled-state "Own your business. Let us handle
insurance." creative test.

Assets:

- Square: `own-business-handle-insurance-square-1080x1080.png`
- Landscape: `own-business-handle-insurance-landscape-1200x628.png`
- Google fallback portrait derivative: `own-business-handle-insurance-portrait-padded-1080x1920.png`
- Moda metadata: `moda_metadata.json`
- Meta handoff: `INFO.md`
- Google readback: `google_ads_readback.json`

Generation command used:

```sh
python3 scripts/moda_generate_own_business_assets.py
```

To conserve Moda credits, this run used one `lite` Moda square generation and
created the landscape and portrait formats locally from the approved square
asset.

Moda output:

- Task: `task_4X68C2FG1G9R3SSER2HA52YDX4`
- Canvas: `cvs_1WHG24DYJV96AVVEESRV54392Y`
- Brand kit: `bk_0PHT577BFH8E9VV0M9QYNM1M24`
- Generation mode: `single_moda_square_with_local_derivatives`
- Credits remaining after generation: `1290`

Paused platform objects:

- Meta campaign: `120248011749820170`
- Meta ad set: `120248011750720170`
- Meta creative: `1552847629515540`
- Meta ad: `120248011752520170`
- Google Demand Gen campaign: `23842205493`
- Google Demand Gen budget: `15572396876`
- Google Demand Gen ad group: `199003668400`
- Google Demand Gen ad: `808769311863`

Current state:

- Meta/Facebook Feed remains paused pending review.
- Google Demand Gen remains paused pending policy review.
- Existing hourly follow-up automation `check-google-ad-review` was updated to
  activate this Meta/Google stack only after reviews clear.

Validation and creation commands:

```sh
/Users/dax/.cache/bomi-ads-venv/bin/python scripts/meta_create_own_business_pooled.py
/Users/dax/.cache/bomi-ads-venv/bin/python scripts/meta_create_own_business_pooled.py --apply
python3 scripts/google_ads_create_own_business_demand_gen.py
python3 scripts/google_ads_create_own_business_demand_gen.py --apply
```
