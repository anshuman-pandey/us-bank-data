# Continue research in BanksOnSale

The open package works independently of a BanksOnSale subscription. You can keep
its samples, notebook results and source-linked exports without registering.

For a selected institution, open its public summary using its FDIC CERT:

```python
url = f"https://www.banksonsale.com/banks/{panel.document['bank']['cert']}"
print(url)
```

The public summary links to the bank's guarded research dossier. The hosted
workspace supports saved screens, watchlists, research dossiers, monitoring,
models and supported exports. Some features require Professional access. Current
plans and trial terms are at https://www.banksonsale.com/pricing.

The hosted workspace displays its own financial reporting date and release.
That edition can differ from this package's selected quarter. A bank identity
link is not a claim that the chosen period or every notebook filter will survive
an upgrade/checkout flow. Check the displayed coverage before continuing a
comparison; do not silently substitute a different bank or period.

Links in the package are optional and have no hidden telemetry. This library
never sends names, emails, saved research or usage events to BanksOnSale.
