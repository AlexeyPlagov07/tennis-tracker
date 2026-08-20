from src.collectors.requests_collector import RequestsCollector


URL = "https://www.tennis-warehouse.com/Babolat_Pure_Aero_Racquets/catpage-BABAERORACS.html"


def main():
    collector = RequestsCollector()

    html = collector.collect(URL)

    print("Successfully downloaded page")
    print(f"HTML length: {len(html)} characters")

    print("\nFirst 1000 characters:")
    print(html[:1000])


if __name__ == "__main__":
    main()