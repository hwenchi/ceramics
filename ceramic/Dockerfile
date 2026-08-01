FROM debian:12-slim

# This container runs with all capabilities dropped, so apt's internal
# privilege-drop to the _apt user (for the download step) fails outright —
# even root can't setuid()/setgid() without CAP_SETUID/CAP_SETGID. That
# sandboxing protects a multi-purpose host from a compromised download; a
# disposable, single-tenant, already-fully-root ceramic has no such thing
# to protect, so just tell apt to skip it.
RUN echo 'APT::Sandbox::User "root";' > /etc/apt/apt.conf.d/99no-sandbox

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

WORKDIR /workspace

EXPOSE 7681 8080

CMD ["ttyd", "-W", "-p", "7681", "tmux", "new", "-A", "-s", "main"]
