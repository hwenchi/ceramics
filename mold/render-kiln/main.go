// render-kiln renders pottery's kiln.html template into a static page,
// reading it straight from pottery/templates/kiln.html so it can't drift.
// setup.sh handles copying alpine.min.js and creating directories.
package main

import (
	"flag"
	"html/template"
	"log"
	"os"
)

type kilnPage struct {
	Name     string
	ClayURL  string
	GlazeURL string
	BatURL   string
}

func main() {
	domain := flag.String("domain", "", "base domain, e.g. ceramics.example.com")
	scheme := flag.String("scheme", "https", "http for local testing (no TLS), https once deployed")
	templatePath := flag.String("template", "../../pottery/templates/kiln.html", "path to pottery's kiln.html template")
	out := flag.String("out", "site/index.html", "output file to write the rendered page to")
	flag.Parse()

	if *domain == "" {
		log.Fatal("-domain is required")
	}

	tmpl, err := template.ParseFiles(*templatePath)
	if err != nil {
		log.Fatalf("parse %s: %v", *templatePath, err)
	}

	page := kilnPage{
		Name:     *domain,
		ClayURL:  *scheme + "://clay." + *domain,
		GlazeURL: *scheme + "://" + *domain, // the app itself lives at the bare domain, not a "glaze." subdomain
		BatURL:   *scheme + "://bat." + *domain,
	}

	f, err := os.Create(*out)
	if err != nil {
		log.Fatalf("create %s: %v", *out, err)
	}
	defer f.Close()
	if err := tmpl.Execute(f, page); err != nil {
		log.Fatalf("render kiln.html: %v", err)
	}
}
