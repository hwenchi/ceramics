FROM golang:1.26 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /portal .

FROM gcr.io/distroless/static-debian12
COPY --from=build /portal /portal
USER nonroot:nonroot
EXPOSE 8000
ENTRYPOINT ["/portal"]
