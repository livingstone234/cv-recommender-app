# 11. AWS Infrastructure

This is the part of the project that turns "I built an app" into "I deployed a
production system" — worth documenting carefully since it's likely the section
with the most unfamiliar concepts. Each subsection below maps 1:1 to a term in
[16-concepts-glossary.md](16-concepts-glossary.md) if anything is unclear.

## 11.1 S3 (raw CV storage)

- Bucket: `cv-recommender-uploads-{env}` — versioning **on**, default encryption
  **SSE-S3**, block all public access.
- Lifecycle rule: transition to Glacier after 90 days (candidate documents are
  PII — set retention per compliance needs).

**Why versioning:** protects against accidental overwrite/delete of an uploaded
CV (recovers the previous object version). **Why SSE-S3:** encrypts every
object at rest by default, with AWS managing the encryption keys — the baseline
expectation for storing any personally identifiable information (PII), which a
candidate's CV is. **Why Glacier after 90 days:** CVs are unlikely to be
re-accessed after the initial analysis; moving cold data to Glacier
(AWS's cheap, slow-retrieval archival tier) cuts storage cost without deleting
the data outright.

## 11.2 Secrets Manager

- Secret name: `cv-recommender/{env}/app-secrets` — JSON blob with
  `OPENAI_API_KEY`, `GEMINI_API_KEY`, `MONGODB_URI`, `API_KEY`.
- EC2 instance role for Elastic Beanstalk is granted `secretsmanager:GetSecretValue`
  scoped to this ARN only.

**Why not plain EB environment properties:** EB lets you set env vars directly
in the console/config, but those are visible in plaintext to anyone with
read access to the EB application in the AWS console, and they'd need to be
duplicated per environment by hand. Secrets Manager centralizes them, supports
rotation, and the **scoped IAM policy** (`GetSecretValue` on this one ARN, not
`secretsmanager:*` on everything) means a compromised EC2 instance can only ever
read this one secret — not every secret in the AWS account. This is the
**principle of least privilege** in practice, and it's worth being able to
point at this specific IAM policy as an example if asked about security
practices in an interview.

## 11.3 Elastic Beanstalk (backend)

- Platform: **Docker on Amazon Linux 2023**.
- Environment tier: web server, load-balanced, min 2 / max 4 instances
  (Auto Scaling on CPU > 60%).
- `.ebextensions/01_environment.config` pulls secrets at instance boot:

```yaml
# .ebextensions/01_environment.config
container_commands:
  01_fetch_secrets:
    command: "python3 scripts/load_secrets_to_env.py"
option_settings:
  aws:autoscaling:asg:
    MinSize: 2
    MaxSize: 4
  aws:elasticbeanstalk:environment:
    LoadBalancerType: application
  aws:elasticbeanstalk:healthreporting:system:
    SystemType: enhanced
```

**What Elastic Beanstalk actually is:** a managed orchestration layer over
plain EC2 — you give it a Docker image (or a zip of app code), and it handles
provisioning EC2 instances, wiring them into an Auto Scaling Group and Load
Balancer, rolling deploys, and health monitoring, without you hand-writing that
infrastructure. It's a middle ground between "raw EC2, configure everything
yourself" and "a PaaS like Heroku, no AWS visibility at all" — you still see
and can inspect the underlying EC2/ASG/ALB resources it creates.

**Why min 2 instances, not 1:** running behind a load balancer with only one
instance means zero redundancy — an instance failure or a deploy takes the
whole service down. Min 2 means there's always a second instance serving
traffic during a rolling deploy or an instance health-check failure.

**`container_commands` vs `commands`:** `.ebextensions` container commands run
*after* the application version is extracted but *before* the web server
starts — the right hook point for "fetch secrets and write them somewhere the
app can read at startup," since the app process needs those secrets available
the moment it boots.

## 11.4 Application Load Balancer

- Listener 443 (ACM cert) → target group on container port 8000.
- Health check path: `/health`.

The ALB terminates TLS (using a certificate from ACM, AWS's certificate
manager) and forwards plain HTTP internally to the EC2 instances' container
port — the instances themselves don't need to handle certificates. It also
continuously polls `/health` on each instance and stops routing traffic to any
instance that fails the check, which is what makes the "min 2 instances"
redundancy above actually meaningful in practice (a failing instance gets
traffic pulled from it automatically, not just left serving errors).

## 11.5 EC2

- Instance type: `t3.small` (dev) / `t3.medium` (prod), inside a **private
  subnet** with NAT for outbound LLM API calls; ALB in the **public subnet**.

This is the standard "public-facing load balancer, private application tier"
network topology: the EC2 instances running your FastAPI app have no public IP
and cannot be reached directly from the internet — all inbound traffic must go
through the ALB. Outbound traffic (the app calling OpenAI/Gemini's APIs) still
needs internet access, which is what the **NAT gateway** provides — it lets a
private-subnet instance initiate outbound connections without being reachable
from outbound.

## 11.6 CodePipeline (backend deploy)

1. **Source**: GitHub (via CodeStar connection), triggers on push to `main`
   (prod) / `develop` (dev).
2. **Build**: CodeBuild — `docker build`, run `pytest`, push image to ECR.
3. **Deploy**: Elastic Beanstalk deploy action, per-environment application
   versions.

Note this is a *second*, AWS-native pipeline described alongside the GitHub
Actions pipelines in [12-cicd.md](12-cicd.md) — in practice a real project
picks **one** deployment mechanism (this project's actual CI/CD is the GitHub
Actions workflows in section 12, which call `beanstalk-deploy` directly). This
CodePipeline description documents the AWS-native alternative for completeness
(and because CodePipeline + CodeBuild + ECR is itself a commonly-asked-about
AWS pattern worth being conversant in), not as a second pipeline to actually
stand up alongside GitHub Actions.

See [16-concepts-glossary.md](16-concepts-glossary.md) for: IAM role/policy,
Auto Scaling Group, ACM, NAT gateway, ECR, CodeBuild.
