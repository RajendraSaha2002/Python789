import json
import socket
import threading
import urllib.parse
import urllib.request


WORDLIST = [
    "www", "api", "app", "admin", "admin1", "portal", "dashboard",
    "login", "auth", "mail", "smtp", "imap", "pop", "webmail",
    "dev", "test", "stage", "staging", "beta", "demo", "uat",
    "prod", "production", "cdn", "static", "assets", "media",
    "images", "img", "files", "download", "uploads", "docs",
    "wiki", "blog", "shop", "store", "support", "help", "status",
    "monitor", "vpn", "remote", "git", "gitlab", "github",
    "jenkins", "ci", "registry", "db", "database", "internal",
]


class SubdomainEnumerator:
    def __init__(self, domain, workers=15, check_http=True):
        self.domain = domain.lower().strip()
        self.workers = workers
        self.check_http = check_http
        self.results = {}
        self.lock = threading.Lock()

    def resolve_subdomain(self, subdomain):
        record = {
            "hostname": subdomain,
            "addresses": [],
            "http_status": "",
            "https_status": "",
        }

        try:
            addresses = socket.getaddrinfo(
                subdomain,
                None,
                type=socket.SOCK_STREAM,
            )

            unique_ips = sorted(
                {
                    item[4][0]
                    for item in addresses
                }
            )

            record["addresses"] = unique_ips

        except socket.gaierror:
            return None

        if self.check_http:
            record["http_status"] = self.check_http_status(
                subdomain,
                "http",
            )

            record["https_status"] = self.check_http_status(
                subdomain,
                "https",
            )

        return record

    @staticmethod
    def check_http_status(hostname, scheme):
        url = f"{scheme}://{hostname}/"

        request = urllib.request.Request(
            url,
            method="HEAD",
            headers={
                "User-Agent": "Authorized-Subdomain-Enumerator/1.0",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=5,
            ) as response:
                return str(response.status)

        except urllib.error.HTTPError as error:
            return str(error.code)

        except Exception:
            return "Unavailable"

    def worker(self, queue):
        while True:
            with self.lock:
                if not queue:
                    return

                subdomain = queue.pop()

            result = self.resolve_subdomain(subdomain)

            if result:
                with self.lock:
                    self.results[subdomain] = result

                print(
                    f"Found: {subdomain} -> "
                    f"{', '.join(result['addresses'])}"
                )

    def enumerate_wordlist(self):
        queue = [
            f"{word}.{self.domain}"
            for word in WORDLIST
        ]

        threads = []

        for _ in range(self.workers):
            thread = threading.Thread(
                target=self.worker,
                args=(queue,),
                daemon=True,
            )

            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    def query_certificate_transparency(self):
        query = urllib.parse.quote(f"%.{self.domain}")

        url = (
            "https://crt.sh/?q="
            f"{query}&output=json"
        )

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Authorized-Subdomain-Enumerator/1.0",
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=25,
            ) as response:
                raw_data = response.read().decode(
                    "utf-8",
                    errors="replace",
                )

            certificates = json.loads(raw_data)

        except Exception as error:
            print(f"CT log query failed: {error}")
            return []

        names = set()

        for certificate in certificates:
            name_value = certificate.get("name_value", "")

            for name in name_value.splitlines():
                name = name.lower().strip()

                if name.startswith("*."):
                    name = name[2:]

                if (
                    name == self.domain
                    or name.endswith(f".{self.domain}")
                ):
                    names.add(name)

        return sorted(names)

    def collect_ct_hosts(self):
        ct_hosts = self.query_certificate_transparency()

        for hostname in ct_hosts:
            if hostname in self.results:
                continue

            result = self.resolve_subdomain(hostname)

            if result:
                self.results[hostname] = result

        return ct_hosts

    def run(self):
        print("\nRunning bounded DNS wordlist checks...")
        self.enumerate_wordlist()

        print("\nQuerying Certificate Transparency logs...")
        ct_hosts = self.collect_ct_hosts()

        return {
            "target_domain": self.domain,
            "wordlist_size": len(WORDLIST),
            "certificate_transparency_names": ct_hosts,
            "found_hosts": sorted(
                self.results.values(),
                key=lambda item: item["hostname"],
            ),
            "found_count": len(self.results),
        }


def print_report(report):
    print("\n" + "=" * 72)
    print("AUTHORIZED SUBDOMAIN ENUMERATION REPORT")
    print("=" * 72)
    print(f"Target domain: {report['target_domain']}")
    print(f"Wordlist entries checked: {report['wordlist_size']}")
    print(
        "Certificate Transparency names found: "
        f"{len(report['certificate_transparency_names'])}"
    )
    print(f"Resolved hosts found: {report['found_count']}")

    print("\nResolved hosts:")

    if not report["found_hosts"]:
        print("  None found.")
        return

    for host in report["found_hosts"]:
        print(f"\n  Host: {host['hostname']}")
        print(f"  IP addresses: {', '.join(host['addresses'])}")

        if host["http_status"]:
            print(f"  HTTP status: {host['http_status']}")

        if host["https_status"]:
            print(f"  HTTPS status: {host['https_status']}")


def main():
    print("Authorized Subdomain Enumerator")
    print("=" * 72)
    print("Use only on a domain you own or have permission to test.\n")

    domain = input("Target domain: ").strip().lower()

    confirmation = input(
        "Type I AUTHORIZE to confirm authorization: "
    ).strip()

    if confirmation != "I AUTHORIZE":
        print("Cancelled: authorization confirmation was not provided.")
        return

    http_choice = input(
        "Check HTTP/HTTPS response status? (y/n) [y]: "
    ).strip().lower()

    check_http = http_choice != "n"

    try:
        enumerator = SubdomainEnumerator(
            domain=domain,
            workers=15,
            check_http=check_http,
        )

        report = enumerator.run()
        print_report(report)

        save_choice = input(
            "\nSave JSON report? (y/n): "
        ).strip().lower()

        if save_choice == "y":
            output_file = "subdomain_enumeration_report.json"

            with open(output_file, "w", encoding="utf-8") as file_handle:
                json.dump(report, file_handle, indent=2)

            print(f"Saved report: {output_file}")

    except KeyboardInterrupt:
        print("\nEnumeration cancelled.")

    except Exception as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()