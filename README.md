# Personal Website

Static personal website for Chinmoy Biswas.

## Editing workflow

1. Open this folder in VS Code: `D:\personal website`
2. Edit files in `src/` and assets in `docs/`
3. Preview locally with `src/index.html`
4. Commit and push:

```powershell
git add .
git commit -m "Update website"
git push -u origin main
```

GitHub Actions deploys `src/` as the website root and copies `docs/` as the asset folder.