# 12. GitHub Actions (Dev / Prod)

This is the pipeline that's actually wired up for this project (see the note at
the end of [11-aws-infrastructure.md](11-aws-infrastructure.md#116-codepipeline-backend-deploy)
about CodePipeline being documented separately but not run in parallel with this).

## `.github/workflows/dev.yml`

```yaml
name: Deploy Dev
on:
  push:
    branches: [develop]
jobs:
  test-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - name: Install system dependencies (poppler, LibreOffice)
        run: sudo apt-get update && sudo apt-get install -y poppler-utils libreoffice-writer
      - run: pip install -r requirements-dev.txt
      - run: pytest
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_DEV }}
          aws-region: eu-west-1
      - name: Deploy to Elastic Beanstalk (dev)
        uses: einaregilsson/beanstalk-deploy@v22
        with:
          aws_access_key: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws_secret_key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          application_name: cv-recommender
          environment_name: cv-recommender-dev
          region: eu-west-1
          version_label: dev-${{ github.sha }}
          deployment_package: deploy.zip
```

`.github/workflows/prod.yml` is the same shape, triggered on push to `main`,
using `AWS_ROLE_PROD` / `cv-recommender-prod`, and running `pytest` **with** the
coverage gate (`--cov=app --cov-fail-under=80`) rather than plain `pytest`.

**The system dependency step was added, not in the original spec.** Caught
while implementing [file parsing](02-architecture.md): `pdf2image` and the
DOCX→PDF conversion path both shell out to OS-level binaries
(`poppler-utils`, `libreoffice-writer` — see
[14-environment-and-requirements.md](14-environment-and-requirements.md)) that
GitHub's `ubuntu-latest` runners don't have preinstalled. Without this step,
`pip install -r requirements-dev.txt` succeeds but the file-parsing tests fail
on first run in CI — a gap that's easy to miss locally if your own machine
already happens to have both installed. `pip install -r requirements-dev.txt`
(not `requirements.txt`) is what pulls in `pytest` and the rest of the test
tooling that plain `requirements.txt` no longer includes — see
[14-environment-and-requirements.md](14-environment-and-requirements.md) for
why they're split. `libreoffice-writer` in particular is still a sizeable
package even without the full suite; expect this step to add real time to
every CI run, which is worth
knowing before wondering why a "just running tests" pipeline got slow.

## Why two branches, two workflows, two AWS environments

`develop` → dev environment, `main` → prod environment is the simplest version
of a **trunk-based / environment-branch** deploy strategy: merging into
`develop` is low-stakes (deploys to an environment nobody but you depends on),
merging into `main` is the real release. Keeping them as fully separate GitHub
Actions workflow files (rather than one workflow with an `if: branch == ...`)
keeps prod's extra safeguards (the coverage gate, the `environment: production`
protection rule) visually obvious in a diff, rather than buried in conditionals.

## `role-to-assume` — why OIDC federation, not long-lived access keys

`aws-actions/configure-aws-credentials@v4` with `role-to-assume` uses GitHub's
OIDC (OpenID Connect) identity provider to let the Actions runner assume an AWS
IAM role **temporarily**, for the duration of the job — no long-lived AWS
access key/secret pair is stored as a GitHub secret at all for this step. This
matters because a leaked long-lived AWS key is a standing risk until manually
rotated; a leaked OIDC-derived session token expires on its own within the
hour and can only ever be minted by GitHub Actions runs from this specific
repo (the trust policy on the IAM role restricts who can assume it). The
`beanstalk-deploy` action's own `aws_access_key`/`aws_secret_key` inputs in the
example above are a simpler, less secure alternative — worth noting the two
approaches aren't meant to run together in practice; the OIDC role assumption
is the one to keep.

## The gate that matters most

**Both workflows gate the deploy step behind a passing test suite** — a
failing `pytest` run stops the pipeline before any AWS action executes. This is
the actual enforcement mechanism behind the ≥80% coverage requirement in
[10-testing-strategy.md](10-testing-strategy.md): it's not just a local
convention, a broken/under-tested change *cannot reach prod* through this
pipeline. If you're asked "how do you know your CI/CD actually enforces
quality, not just runs tests for show" — this is the concrete answer: the
deploy step has a hard dependency on the test step succeeding.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: OIDC, IAM role,
trunk-based development, CI/CD gate.
