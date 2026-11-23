FROM python:3.12-slim-bookworm@sha256:e697c81897302a4c4333bade000d98038fbb21eb064f8ee1fd42d02ebcd9d337

RUN apt-get update \
    && apt-get install -y --no-install-recommends bash ca-certificates curl git procps ripgrep xz-utils \
    && rm -rf /var/lib/apt/lists/*

RUN set -eu; \
    case "$(dpkg --print-architecture)" in \
      arm64) arch=arm64; sha=2babb9eb5264860d540849f4b064a6fbdebcdc323657d9d382ce23d313fd5e09 ;; \
      amd64) arch=x64; sha=cdeb8670a0c81f51b4dc4ac61919f9b1ad917b304bf8221eb939570663d240f8 ;; \
      *) echo "Unsupported Node.js architecture" >&2; exit 1 ;; \
    esac; \
    curl -fsSL --retry 3 -o /tmp/node.tar.xz "https://nodejs.org/dist/v22.23.5/node-v22.23.5-linux-${arch}.tar.xz"; \
    echo "$sha  /tmp/node.tar.xz" | sha256sum -c -; \
    tar -xJf /tmp/node.tar.xz --strip-components=1 -C /usr/local; \
    rm /tmp/node.tar.xz

WORKDIR /opt/sonar-agents
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund \
    && for cli in codex claude pi opencode copilot; do ln -s "/opt/sonar-agents/node_modules/.bin/$cli" "/usr/local/bin/$cli"; done \
    && npm cache clean --force

# Harbor's Pi adapter sources this path before launching the system-wide Node CLI.
RUN mkdir -p /etc/skel/.nvm /root/.nvm \
    && echo 'export PATH="/usr/local/bin:$PATH"' > /etc/skel/.nvm/nvm.sh \
    && cp /etc/skel/.nvm/nvm.sh /root/.nvm/nvm.sh

WORKDIR /app
