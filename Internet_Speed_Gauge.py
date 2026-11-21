
import speedtest
import plotly.graph_objects as go
from datetime import datetime
import os
import webbrowser


def measure_internet_speed():

    print("\n===================================")
    print("       INTERNET SPEED GAUGE")
    print("===================================")

    try:
        print("\n[+] Initializing speed test...")

        st = speedtest.Speedtest()

        print("[+] Finding the best server...")
        st.get_best_server()

        print("[+] Measuring download speed...")
        download_speed = st.download() / 1_000_000

        print("[+] Measuring upload speed...")
        upload_speed = st.upload() / 1_000_000

        ping = st.results.ping

        download_speed = round(download_speed, 2)
        upload_speed = round(upload_speed, 2)
        ping = round(ping, 2)

        print("\n========== SPEED TEST RESULTS ==========")
        print(f"Download Speed : {download_speed} Mbps")
        print(f"Upload Speed   : {upload_speed} Mbps")
        print(f"Ping           : {ping} ms")
        print("========================================")

        return download_speed, upload_speed, ping

    except Exception as error:

        print("\n[!] Speed test failed!")
        print("Error:", error)

        return None


def create_speed_gauge(download, upload, ping):

    fig = go.Figure()

    # Download gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=download,
            title={
                "text": "Download Speed (Mbps)"
            },
            domain={
                "x": [0, 1],
                "y": [0.55, 1]
            },
            gauge={
                "axis": {"range": [0, 300]},
                "bar": {"color": "#00C853"},
                "steps": [
                    {
                        "range": [0, 50],
                        "color": "#FFCDD2"
                    },
                    {
                        "range": [50, 150],
                        "color": "#FFF9C4"
                    },
                    {
                        "range": [150, 300],
                        "color": "#C8E6C9"
                    }
                ]
            }
        )
    )

    # Upload gauge
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=upload,
            title={
                "text": "Upload Speed (Mbps)"
            },
            domain={
                "x": [0, 1],
                "y": [0.05, 0.48]
            },
            gauge={
                "axis": {"range": [0, 300]},
                "bar": {"color": "#2196F3"}
            }
        )
    )

    fig.update_layout(
        title={
            "text": (
                "LIVE INTERNET SPEED ANALYSIS"
                f"<br><sup>Ping: {ping} ms</sup>"
            ),
            "x": 0.5
        },
        template="plotly_dark",
        height=800
    )

    os.makedirs("reports", exist_ok=True)

    filename = (
        "reports/internet_speed_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".html"
    )

    fig.write_html(filename)

    print("\n[+] Dashboard generated:", filename)

    fig.show()


def main():

    result = measure_internet_speed()

    if result is None:
        return

    download, upload, ping = result

    create_speed_gauge(
        download,
        upload,
        ping
    )


if __name__ == "__main__":
    main()
