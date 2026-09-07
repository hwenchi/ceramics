FROM debian:12-slim

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        tmux \
        curl \
        ca-certificates \
        git \
        gnupg \
        python3 \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN case "$(dpkg --print-architecture)" in \
        amd64) ARCH=x86_64 ;; \
        arm64) ARCH=aarch64 ;; \
        *) echo "unsupported architecture" >&2; exit 1 ;; \
    esac \
    && curl -fsSL -o /usr/local/bin/ttyd \
        "https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.${ARCH}" \
    && chmod +x /usr/local/bin/ttyd

ENV DUFS_VERSION=v0.46.0
RUN case "$(dpkg --print-architecture)" in \
        amd64) ARCH=x86_64 ;; \
        arm64) ARCH=aarch64 ;; \
        *) echo "unsupported architecture" >&2; exit 1 ;; \
    esac \
    && curl -fsSL -o /tmp/dufs.tar.gz \
        "https://github.com/sigoden/dufs/releases/download/${DUFS_VERSION}/dufs-${DUFS_VERSION}-${ARCH}-unknown-linux-musl.tar.gz" \
    && tar -xzf /tmp/dufs.tar.gz -C /usr/local/bin dufs \
    && chmod +x /usr/local/bin/dufs \
    && rm -rf /tmp/dufs*

RUN npm install -g @anthropic-ai/claude-code

COPY CLAUDE.md /root/.claude/CLAUDE.md
COPY start.sh /usr/local/bin/start.sh
COPY console-server.py /opt/console-server.py
COPY recipes/ /opt/recipes/
COPY skills/recipes/ /root/.claude/skills/recipes/
RUN chmod +x /usr/local/bin/start.sh

WORKDIR /workspace

EXPOSE 7681 8080 8081 8082

CMD ["start.sh"]
