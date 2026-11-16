"""Future HTTP runner: probes only; not an end-to-end financial test."""
import httpx


def main():
    failures = 0
    with httpx.Client(timeout=3, trust_env=False, follow_redirects=False) as client:
        for name, port, path in [('coredb', 8012, '/coredb/salud'),
                                 ('captacion', 8014, '/ready'), ('sol', 8011, '/health'),
                                 ('evaluacion', 8015, '/salud')]:
            try:
                response = client.get(f'http://{name}:{port}{path}')
                print(name, path, response.status_code)  # never body/headers/credentials
                failures += int(response.status_code != 200)
            except httpx.HTTPError:
                print(name, 'TRANSPORT_ERROR')
                failures += 1
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
