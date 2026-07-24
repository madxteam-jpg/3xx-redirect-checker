import io
import matplotlib.pyplot as plt
import pandas as pd
import requests
import streamlit as st


def check_url(url: str, max_redirects: int = 10, timeout: int = 5) -> dict:
    """Checks a URL for redirects, chains, and loops."""
    url = url.strip()

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
            if current_url in history:
                chain_str = " -> ".join(history + [current_url])
                return {
                    "URL": url,
                    "Is Redirected": "Redirected - Notify SME",
                    "Chain/Loop Status": "Loop Detected",
                    "Redirect Count": len(history) - 1,
                    "Full Chain": chain_str,
                }

            history.append(current_url)

            response = session.get(
                current_url, allow_redirects=False, timeout=timeout
            )

            if 300 <= response.status_code < 400:
                location = response.headers.get("Location")
                if not location:
                    return {
                        "URL": url,
                        "Is Redirected": "Redirected - Notify SME",
                        "Chain/Loop Status": "Broken Redirect (Missing Location)",
                        "Redirect Count": len(history) - 1,
                        "Full Chain": " -> ".join(history),
                    }
                current_url = requests.compat.urljoin(current_url, location)
            else:
                redirect_count = len(history) - 1
                chain_str = " -> ".join(history)

                if redirect_count == 0:
                    return {
                        "URL": url,
                        "Is Redirected": "Not redirected - Good",
                        "Chain/Loop Status": "Clean (No Chain/Loop)",
                        "Redirect Count": 0,
                        "Full Chain": chain_str,
                    }
                elif redirect_count == 1:
                    return {
                        "URL": url,
                        "Is Redirected": "Redirected - Notify SME",
                        "Chain/Loop Status": "Single Redirect",
                        "Redirect Count": 1,
                        "Full Chain": chain_str,
                    }
                else:
                    return {
                        "URL": url,
                        "Is Redirected": "Redirected - Notify SME",
                        "Chain/Loop Status": "Redirect Chain Detected",
                        "Redirect Count": redirect_count,
                        "Full Chain": chain_str,
                    }

        return {
            "URL": url,
            "Is Redirected": "Redirected - Notify SME",
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


def dataframe_to_image(df: pd.DataFrame) -> bytes:
    """Renders a pandas DataFrame as a clean PNG image in memory."""
    fig, ax = plt.subplots(
        figsize=(
            max(10, len(df.columns) * 2.8),
            max(3, len(df) * 0.6 + 1.5),
        )
    )
    ax.axis("tight")
    ax.axis("off")

    table = ax.table(
        cellText=df.values, colLabels=df.columns, cellLoc="left", loc="center"
    )

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.8)

    # Style header and alternating rows
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight="bold", color="white")
            cell.set_facecolor("#1e293b")  # Dark slate header
        else:
            if row % 2 == 0:
                cell.set_facecolor("#f8fafc")  # Subtle zebra striping
            else:
                cell.set_facecolor("#ffffff")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=200)
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# --- Streamlit UI ---
st.set_page_config(
    page_title="URL Redirect & Loop Checker", page_icon="🔗", layout="wide"
)

st.title("🔗 URL Redirect & Loop Checker")
st.write("Enter one URL per line to assess redirect status and chains.")

urls_input = st.text_area(
    "Paste URLs here:",
    height=180,
    placeholder="https://example.com\nhttp://httpbin.org/redirect/1\nhttp://httpbin.org/absolute-3xx/3",
)

if st.button("Check URLs", type="primary"):
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
            status_text.text(
                f"Checking ({idx + 1}/{len(url_list)}): {target_url}"
            )
            res = check_url(target_url)
            results.append(res)
            progress_bar.progress((idx + 1) / len(url_list))

        status_text.empty()
        progress_bar.empty()

        df = pd.DataFrame(results)
        st.session_state["results_df"] = df

if "results_df" in st.session_state:
    df = st.session_state["results_df"]

    st.subheader("Results")
    st.dataframe(
        df,
        column_config={
            "URL": st.column_config.TextColumn("Original URL", width="medium"),
            "Is Redirected": st.column_config.TextColumn(
                "Is Redirected", width="medium"
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

    # Convert table to PNG image bytes
    img_bytes = dataframe_to_image(df)

    # Download Button for Image
    st.download_button(
        label="📸 Download Results as Image (PNG)",
        data=img_bytes,
        file_name="url_redirect_results.png",
        mime="image/png",
    )
