# Publishing alabofur

Step-by-step guide to build, **sign** and publish alabofur on every channel:
GitHub Releases, an apt repository and a yum/dnf repository.

Channels and how a user installs from each:

| Channel | User installs with | Hosted on |
| --- | --- | --- |
| apt repo | `apt install alabofur` | GitHub Pages |
| yum/dnf repo | `dnf install alabofur` | GitHub Pages |
| GitHub Releases | download `.deb`/`.rpm` | GitHub |

GitHub repo: `github.com/tuncaybahadir/alabofur` → Pages URL
`https://tuncaybahadir.github.io/alabofur/`.

---

## Step 1 — Tools and accounts (one-time)

Local tools (Linux or WSL):

```bash
# nfpm builds the .deb/.rpm; repo tooling signs and indexes them
echo 'deb [trusted=yes] https://repo.goreleaser.com/apt/ /' | sudo tee /etc/apt/sources.list.d/goreleaser.list
sudo apt update
sudo apt install -y nfpm dpkg-dev apt-utils createrepo-c gnupg
```

Accounts: a GitHub account (the repo).

---

## Step 2 — Create the GPG signing key (one-time)

The apt/yum repositories are signed so clients can verify them. Generate a key
**once** and reuse it for every release.

```bash
cat >/tmp/keygen <<'EOF'
%no-protection
Key-Type: RSA
Key-Length: 4096
Name-Real: alabofur package signing
Name-Email: tuncaybahadir@protonmail.com
Expire-Date: 0
%commit
EOF
gpg --batch --generate-key /tmp/keygen
gpg --list-secret-keys --keyid-format=long tuncaybahadir@protonmail.com
```

Export the **private** key so GitHub Actions can sign during a release:

```bash
gpg --armor --export-secret-keys tuncaybahadir@protonmail.com
```

In GitHub: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
| --- | --- |
| `GPG_PRIVATE_KEY` | the full `-----BEGIN PGP PRIVATE KEY BLOCK-----` output above |
| `GPG_PASSPHRASE` | empty if you used `%no-protection`, otherwise the passphrase |

> Keep the private key safe; never commit it. Only the public key is published
> (clients fetch it from Pages to verify the repos).

---

## Step 3 — Push the code and enable Pages (one-time)

```bash
cd alabofur
git init -b main
git add .
git commit -m "alabofur 1.0.0"
git remote add origin https://github.com/tuncaybahadir/alabofur.git
git push -u origin main           # add --force if replacing old content
```

Then on GitHub: **Settings → Pages → Build and deployment → Source = "GitHub
Actions"**.

---

## Step 4 — Release apt + yum + GitHub Releases (automated)

Everything below is done by [.github/workflows/release.yml](.github/workflows/release.yml)
when you push a version tag. To cut a release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow then:

1. builds `.deb`, `.rpm` and a `.tar.gz` with nfpm;
2. attaches them to a **GitHub Release**;
3. runs [packaging/build-repo.sh](packaging/build-repo.sh) to build an apt repo
   (signed `InRelease`/`Release.gpg`) and a yum repo (signed `repomd.xml`),
   plus a landing page, and deploys it to **GitHub Pages**.

When it finishes, the install commands in the README work:

```bash
# Debian / Ubuntu
curl -fsSL https://tuncaybahadir.github.io/alabofur/alabofur.asc | sudo gpg --dearmor -o /usr/share/keyrings/alabofur.gpg
echo "deb [signed-by=/usr/share/keyrings/alabofur.gpg] https://tuncaybahadir.github.io/alabofur/deb ./" | sudo tee /etc/apt/sources.list.d/alabofur.list
sudo apt update && sudo apt install alabofur

# Fedora / RHEL / CentOS
sudo curl -fsSL https://tuncaybahadir.github.io/alabofur/rpm/alabofur.repo -o /etc/yum.repos.d/alabofur.repo
sudo rpm --import https://tuncaybahadir.github.io/alabofur/alabofur.asc
sudo dnf install alabofur
```

For every later release: bump the version (Makefile `VERSION`,
`packaging/nfpm.yaml`, `bin/alabofur`, the man page),
commit, then push a new `v*` tag.

### Build the packages locally (optional)

```bash
make deb     # -> alabofur_1.0.0_all.deb
make rpm     # -> alabofur-1.0.0-1.noarch.rpm
```
