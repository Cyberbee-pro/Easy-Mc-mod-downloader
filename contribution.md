## CI/CD Automation Framework

The pipeline defined in `.github/workflows/release.yml` automates testing, incremental version calculations, and production distribution deployment whenever updates are pushed to the `main` or `master` branches.

### Production Release Routine

The deployment architecture uses specific string patterns within your Git commit messages to govern output workflows:

* **Official Production Release:** Append `-prod` to the end of your commit message.
```bash
git commit -m "Feature deployment pass -prod"

```

The pipeline sets compilation vectors, calculates the next chronological version tag (`v1.X`), creates a live Git tag, packages the executable inside an Arch Linux container, and posts a live production release page with the compiled Linux binary attached.
* **Non-Production Pre-Release:** Append `-noprod` to the end of your commit message.
```bash
git commit -m "Alpha staging update -noprod"

```


Executes the same automation and compilation sweeps as a production run, but flags the final target on the GitHub Release UI explicitly as a pre-release asset for experimental testing.
* **Compilation Sanity Check:** Omitting both configuration flags runs the setup parameters and PyInstaller processes to ensure code compliance and structure sanity, but terminates prior to altering the Git log repository states or publishing live files.