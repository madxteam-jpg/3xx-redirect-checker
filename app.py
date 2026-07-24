import pandas as pd
import requests
import streamlit as st


def check_url(url: str, max_redirects: int = 10, timeout: int = 5) -> dict:
    """Checks a URL for redirects, chains, and loops."""
    url = url.strip()

    # Prepend scheme if missing
    if not url.startswith(("http://", "https://")):
        url = "http://" + url

    history = []
    current_url = url

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0"
            )
        }
    )

    try:
        while len(history) <= max_redirects:
            # Check for loop
            if current_url in history:
                chain_str = " -> ".join(history + [current_url])
                return {
                    "URL": url,
                    "Is Redirected": "Redirected",
                    "Chain/Loop Status": "Loop Detected",
                    "Redirect Count": len(history) - 1,
                    "Full Chain": chain_str,
                }

            history.append(current_url)

            response = session.get(
                current_url, allow_redirects=False, timeout=timeout
            )

            # 3xx Status Code Check
            if 300 <= response.status_code < 400:
                location = response.headers.get("Location")
                if not location:
                    return {
                        "URL": url,
                        "Is Redirected": "Redirected",
                        "Chain/Loop Status": "Broken Redirect (Missing Location)",
                        "Redirect Count": len(history) - 1,
                        "Full Chain": " -> ".join(history),
                    }
                # Handle relative URLs
                current_url = requests.compat.urljoin(current_url, location)
            else:
                # Terminal response reached
                redirect_count = len(history) - 1
                chain_str = " -> ".join(history)

                if redirect_count == 0:
                    return {
                        "URL": url,
                        "Is Redirected": "Not Redirected",
                        "Chain/Loop Status": "Clean (No Chain/Loop)",
                        "Redirect Count": 0,
                        "Full Chain": chain_str,
                    }
                elif redirect_count == 1:
                    return {
                        "URL": url,
                        "Is Redirected": "Redirected",
                        "Chain/Loop Status": "Single Redirect",
                        "Redirect Count": 1,
                        "Full Chain": chain_str,
                    }
                else:
                    return {
                        "URL": url,
                        "Is Redirected": "Redirected",
                        "Chain/Loop Status": "Redirect Chain Detected",
                        "Redirect Count": redirect_count,
                        "Full Chain": chain_str,
                    }

        # Exceeded limit
        return {
            "URL": url,
            "Is Redirected": "Redirected",
            "Chain/Loop Status": "Max Redirects Exceeded",
            "Redirect Count": len(history) - 1,
            "Full Chain": " -> ".join(history),
        }

    except requests.exceptions.RequestException as e:
        return {
            "URL": url,
            "Is Redirected": "Error",
            "Chain/Loop Status": f"Connection Error: {type(e).__name__}",
            "Redirect Count": len(history) - 1,
            "Full Chain": " -> ".join(history) if history else url,
        }


# --- Streamlit UI ---
st.set_page_config(
    page_title="URL Redirect & Loop Checker", page_icon="🔗", layout="wide"
)

st.title("🔗 URL Redirect & Loop Checker")
st.write("Enter one URL per line to assess redirect status and chains.")

# Multiline text input
urls_input = st.text_area(
    "Paste URLs here:",
    height=200,
    placeholder="https://example.com\nhttp://httpbin.org/redirect/1\nhttp://httpbin.org/absolute-3xx/3",
)

if st.button("Check URLs", type="primary"):
    # Split input by line and clean empty lines
    url_list = [
        line.strip() for line in urls_input.splitlines() if line.strip()
    ]

    if not url_list:
        st.warning("Please enter at least one URL.")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for idx, target_url in enumerate(url_list):
            status_text.text(f"Checking ({idx + 1}/{len(url_list)}): {target_url}")
            res = check_url(target_url)
            results.append(res)
            progress_bar.progress((idx + 1) / len(url_list))

        status_text.empty()
        progress_bar.empty()

        # Convert to DataFrame
        df = pd.DataFrame(results)

        # Highlight status logic
        st.subheader("Results")
        st.dataframe(
            df,
            column_config={
                "URL": st.column_config.TextColumn("Original URL", width="medium"),
                "Is Redirected": st.column_config.TextColumn(
                    "Is Redirected", width="small"
                ),
                "Chain/Loop Status": st.column_config.TextColumn(
                    "Chain/Loop Status", width="medium"
                ),
                "Redirect Count": st.column_config.NumberColumn(
                    "Hops", width="small"
                ),
                "Full Chain": st.column_config.TextColumn(
                    "Full Path / Chain", width="large"
                ),
            },
            hide_index=True,
            use_container_width=True,
        )

        # Summary Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Checked", len(df))
        col2.metric("Redirected", len(df[df["Is Redirected"] == "Redirected"]))
        col3.metric(
            "Chains Detected",
            len(df[df["Chain/Loop Status"] == "Redirect Chain Detected"]),
        )
        col4.metric(
            "Loops Detected",
            len(df[df["Chain/Loop Status"] == "Loop Detected"]),
        )
