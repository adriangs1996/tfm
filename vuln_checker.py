class VulnerabilityChecker:
    @staticmethod
    def ecosystem_for_language(language: str) -> str:
        if language == "python":
            return "PyPI"
        elif language == "java":
            return "maven"
        else:
            return "npm"


    def __init__(self, dep_name: str, project_language: str):
        self.dep_name = dep_name
        data = {
            "package": {
                "name": dep_name,
                "ecosystem": VulnerabilityChecker.ecosystem_for_language(project_language)
            }
        }
        vuln_db_url = "https://api.osv.dev/v1/query"

        response = requests.post(vuln_db_url, json=data)
        if response.status_code != 200:
            raise Exception("Failed to fetch data from OSV API")

        self.vulnerabilities = response.json().get("vulns", [])

    def vulns_for_algorithm(self, algorithm: str):
        vuln_details_url = "https://api.osv.dev/v1/vulns"
        for vuln in self.vulnerabilities:
            vuln_id = vuln.get("id")
            response = requests.get(f"{vuln_details_url}/{vuln_id}")
            if response.status_code != 200:
                raise Exception("Failed to fetch data from OSV API")
            vuln_details = response.json()
            details = vuln_details.get("details")
            summary = vuln_details.get("summary")

            llm_prompt = f"""
            The package {self.dep_name} was found a vulnerability in the OSV database.
            The vulnerability is described as follows:

            Summary: {summary}
            Details: {details}

            Does the vulnerability affect the algorithm {algorithm}?
            Output a single word and only a single word: 'yes' or 'no'.
            """
            client = Client(host="http://localhost:11434")
            llm_response = client.generate(model="codellama:7b", prompt=llm_prompt, options=options)
            answer = llm_response.get("response")

            print(f"Answer: {answer.strip()}")

            if answer.lower().strip() == "yes":
                yield vuln_details


if __name__ == "__main__":
    import pkg_resources
    from progressbar import progressbar
    for pkg in progressbar(pkg_resources.working_set):
        print(f"\nChecking package {pkg.project_name}")
        for vuln in VulnerabilityChecker(pkg.project_name, "python").vulns_for_algorithm("RSA"):
            current_version = pkg.version
            affected = vuln.get("affected", [])
            for affected_package in affected:
                affected_versions = affected_package.get("versions")
                if current_version in affected_versions:
                    print(f"Package {pkg.project_name} is affected by vulnerability {vuln.get('id')}")
                    print(f"Current version: {current_version}")
                    print(f"Affected versions: {affected_versions}")
                    print(f"Summary: {vuln.get('summary')}")


     
