FROM debian:12-slim

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        bash \
        tmux \
        curl \
        ca-certificates \
        git \
        gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /usr/local/bin/ttyd \
        https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64 \
    && chmod +x /usr/local/bin/ttyd

ENV DUFS_VERSION=v0.46.0
RUN curl -fsSL -o /tmp/dufs.tar.gz \
        "https://github.com/sigoden/dufs/releases/download/${DUFS_VERSION}/dufs-${DUFS_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    && tar -xzf /tmp/dufs.tar.gz -C /usr/local/bin dufs \
    && chmod +x /usr/local/bin/dufs \
    && rm -rf /tmp/dufs*

RUN npm install -g @anthropic-ai/claude-code

COPY CLAUDE.md /root/.claude/CLAUDE.md
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

WORKDIR /workspace

EXPOSE 7681 8080 8082

CMD ["start.sh"]
