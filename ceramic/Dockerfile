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

RUN npm install -g @anthropic-ai/claude-code

COPY CLAUDE.md /root/.claude/CLAUDE.md

WORKDIR /workspace

EXPOSE 7681 8080

CMD ["ttyd", "-W", "-p", "7681", "tmux", "new", "-A", "-s", "main", "claude"]
