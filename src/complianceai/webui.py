"""Streamlit Web UI for ComplianceAI."""

import streamlit as st
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from complianceai.orchestrator import Orchestrator


st.set_page_config(
    page_title="ComplianceAI",
    page_icon="Shield",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    st.title("ComplianceAI")
    st.markdown("### Automated Dependency License Compliance Scanner")
    st.markdown("Analyze your project dependencies for license compliance issues, conflicts, andsecurity risks.")

    with st.sidebar:
        st.header("Input")
        input_method = st.radio(
            "Choose input method:",
            ["Upload File", "Paste Text", "GitHub URL"],
            horizontal=True,
        )

        input_content = ""
        file_name = None

        if input_method == "Upload File":
            uploaded_file = st.file_uploader(
                "Upload dependency file",
                type=["txt", "json"],
                help="Upload requirements.txt or package.json",
            )
            if uploaded_file is not None:
                input_content = uploaded_file.getvalue().decode("utf-8")
                file_name = uploaded_file.name
        elif input_method == "GitHub URL":
            github_url = st.text_input(
                "GitHub Repository URL",
                placeholder="https://github.com/user/repo",
                help="Enter a public GitHub repository URL",
            )
            input_content = github_url
            if github_url:
                file_name = f"github.com/{github_url.split('/')[-2:]}"
        else:
            input_content = st.text_area(
                "Paste dependencies",
                height=200,
                placeholder="numpy==1.24.0\npandas>=1.3.0\nrequests~=2.28.0",
            )

        st.divider()
        st.header("Settings")
        max_depth = st.slider(
            "Dependency crawl depth",
            min_value=1,
            max_value=5,
            value=3,
            help="How many levels deep to crawl transitive dependencies",
        )

    if input_content:
        st.markdown("---")

        col1, col2 = st.columns([1, 4])
        with col1:
            analyze_btn = st.button(
                "Analyze",
                type="primary",
                use_container_width=True,
            )
        with col2:
            if file_name:
                st.info(f"File: {file_name}")
            else:
                st.info("Raw text input")

        if analyze_btn:
            with st.spinner("Analyzing dependencies..."):
                try:
                    orchestrator = Orchestrator(max_depth=max_depth)
                    result = orchestrator.run(input_content)

                    if result.get("success"):
                        display_report(result)
                    else:
                        st.error("Analysis failed. Please check your input.")

                except Exception as e:
                    st.error(f"Error running analysis: {str(e)}")
    else:
        st.info("Upload a file or paste dependencies to begin analysis")

        with st.expander("Example input"):
            st.code("""numpy==1.24.0
pandas>=1.3.0
requests~=2.28.0
flask>=2.0.0
django>=4.0
celery>=5.0""", language="text")


def display_report(result):
    deps_raw = result.get("dependencies", {})
    
    # Handle both dict and list formats
    if isinstance(deps_raw, list):
        dependencies = {d.get("name", "unknown"): d for d in deps_raw}
    else:
        dependencies = deps_raw
    
    conflicts = result.get("conflicts", [])
    report = result.get("report", {})

    st.markdown("## Summary")

    total_deps = len(dependencies)
    critical = sum(1 for c in conflicts if c.get("severity") == "critical")
    warnings = sum(1 for c in conflicts if c.get("severity") == "warning")
    safe = total_deps - critical - warnings

    cols = st.columns(4)
    with cols[0]:
        st.metric("Total Dependencies", total_deps)
    with cols[1]:
        st.metric("Critical Issues", critical, delta_color="inverse")
    with cols[2]:
        st.metric("Warnings", warnings, delta_color="inverse")
    with cols[3]:
        st.metric("Safe", safe, delta_color="normal")

    if conflicts:
        severity_color = "red" if critical > 0 else ("orange" if warnings > 0 else "green")
        if critical > 0:
            st.error(f"Found {critical} critical license conflict(s)! Review the details below.")
        elif warnings > 0:
            st.warning(f"Found {warnings} warning(s). Review for potential issues.")
        else:
            st.success("No significant conflicts found.")
    else:
        st.success("No license conflicts detected.")

    st.markdown("---")
    st.markdown("## Detailed Findings")

    if not conflicts:
        st.info("No conflicts to display.")
    else:
        for i, conflict in enumerate(conflicts, 1):
            severity = conflict.get("severity", "info")
            pkg1 = conflict.get("package1", {})
            pkg2 = conflict.get("package2", {})

            severity_label = severity.upper()
            if severity == "critical":
                color = "#FF4B4B"
                emoji = "⛔"
            elif severity == "warning":
                color = "#FFA500"
                emoji = "⚠️"
            else:
                color = "#4CAF50"
                emoji = "ℹ️"

            with st.container():
                st.markdown(
                    f"""
                    <div style="
                        padding: 12px;
                        border-left: 4px solid {color};
                        background: rgba(255,255,255,0.05);
                        margin-bottom: 8px;
                        border-radius: 0 4px 4px 0;
                    ">
                        <strong>{emoji} {severity_label}</strong> — {conflict.get("description", "License conflict")}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**{pkg1.get('name')}** ({pkg1.get('version', 'unknown')})")
                    st.caption(f"License: {pkg1.get('license', 'Unknown')}")
                with c2:
                    st.markdown(f"**{pkg2.get('name')}** ({pkg2.get('version', 'unknown')})")
                    st.caption(f"License: {pkg2.get('license', 'Unknown')}")

                if conflict.get("recommendation"):
                    st.caption(f"💡 Recommendation: {conflict.get('recommendation')}")

                st.markdown("---")

    st.markdown("## Dependency Overview")

    if dependencies:
        dep_data = []
        if isinstance(dependencies, dict):
            for name, info in dependencies.items():
                dep_data.append({
                    "Package": name,
                    "Version": info.get("version", "unknown") if isinstance(info, dict) else "unknown",
                    "License": info.get("license", "Unknown") if isinstance(info, dict) else "Unknown",
                })
        else:
            for dep in dependencies:
                dep_data.append({
                    "Package": dep.get("name", "unknown"),
                    "Version": dep.get("version", "unknown"),
                    "License": dep.get("license", "Unknown"),
                })

        st.dataframe(
            dep_data,
            column_config={
                "Package": st.column_config.TextColumn("Package", width="medium"),
                "Version": st.column_config.TextColumn("Version", width="small"),
                "License": st.column_config.TextColumn("License", width="small"),
            },
            hide_index=True,
            use_container_width=True,
        )

    errors = result.get("errors")
    if errors:
        with st.expander("View errors"):
            for err in errors:
                st.text(f"{err.get('step')}: {err.get('error')}")


if __name__ == "__main__":
    main()