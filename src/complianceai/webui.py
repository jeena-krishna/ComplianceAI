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
    st.markdown("Analyze your project dependencies for license compliance issues, and security risks.")

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
                # Clean up the display - get owner/repo cleanly
                parts = github_url.strip('/').split('/')
                if len(parts) >= 2:
                    file_name = f"{parts[-2]}/{parts[-1]}"
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
                st.info(f"Source: {file_name}")
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
    
    # Footer
    st.markdown("---")
    st.caption("Built with multi-agent AI architecture • ComplianceAI")


def display_report(result):
    deps_raw = result.get("dependencies", {})
    
    # Handle both dict and list formats
    if isinstance(deps_raw, list):
        dependencies = {d.get("name", "unknown"): d for d in deps_raw}
    else:
        dependencies = deps_raw
    
    # Handle new dict format from conflict_agent or legacy list format
    conflicts_result = result.get("conflicts", [])
    if isinstance(conflicts_result, dict):
        conflicts = conflicts_result.get("conflicts", [])
        undetected_from_conflict = conflicts_result.get("undetected_licenses", [])
    else:
        conflicts = conflicts_result
        undetected_from_conflict = []
    
    report = result.get("report", {})
    
    # Use undetected_licenses from conflict_agent, fallback to manual detection
    if undetected_from_conflict:
        unknown_packages = [
            {"Package": pkg.get("name", ""), "Version": pkg.get("version", "")}
            for pkg in undetected_from_conflict
        ]
    else:
        unknown_packages = [
            {"Package": name, "Version": info.get("version", "")}
            for name, info in dependencies.items()
            if info.get("license") == "Unknown" or not info.get("license")
        ]
    
    # Clean up package names - remove trailing version operators
    for pkg in unknown_packages:
        pkg["Package"] = pkg["Package"].strip("~>=<!")

    # Sort alphabetically
    unknown_packages = sorted(unknown_packages, key=lambda x: x["Package"].lower())
    
    known_packages = [
        {"Package": name, "Version": info.get("version", ""), "License": info.get("license", "Unknown")}
        for name, info in dependencies.items()
        if info.get("license") and info.get("license") != "Unknown"
    ]

    st.markdown("## Summary")

    total_deps = len(dependencies)
    critical = sum(1 for c in conflicts if c.get("severity") == "critical")
    warnings = sum(1 for c in conflicts if c.get("severity") == "warning")
    unknown_count = len(unknown_packages)
    safe = total_deps - unknown_count - len(conflicts)

    cols = st.columns(5)
    with cols[0]:
        st.metric("Total Dependencies", total_deps)
    with cols[1]:
        st.metric("Critical Issues", critical, delta_color="inverse")
    with cols[2]:
        st.metric("Warnings", warnings, delta_color="inverse")
    with cols[3]:
        st.metric("Unknown", unknown_count, delta_color="off")
    with cols[4]:
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
            
            # Handle both field names (packages_1/packages_2 or legacy package1/package2)
            pkgs1 = conflict.get("packages_1", conflict.get("package1", []))
            pkgs2 = conflict.get("packages_2", conflict.get("package2", []))
            
            # Handle list or single item
            if isinstance(pkgs1, list) and pkgs1:
                first_pkg1 = pkgs1[0] if isinstance(pkgs1[0], dict) else pkgs1[0]
                pkg1_name = first_pkg1.get('name') if isinstance(first_pkg1, dict) else str(first_pkg1)
                pkg1_version = first_pkg1.get('version', '') if isinstance(first_pkg1, dict) else ''
            else:
                pkg1_name = str(pkgs1) if pkgs1 else 'N/A'
                pkg1_version = ''
            
            if isinstance(pkgs2, list) and pkgs2:
                first_pkg2 = pkgs2[0] if isinstance(pkgs2[0], dict) else pkgs2[0]
                pkg2_name = first_pkg2.get('name') if isinstance(first_pkg2, dict) else str(first_pkg2)
                pkg2_version = first_pkg2.get('version', '') if isinstance(first_pkg2, dict) else ''
            else:
                pkg2_name = str(pkgs2) if pkgs2 else 'N/A'
                pkg2_version = ''

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
                    st.markdown(f"**{pkg1_name}** ({pkg1_version or 'unknown'})")
                    st.caption(f"License: {conflict.get('license_1', 'Unknown')}")
                with c2:
                    st.markdown(f"**{pkg2_name}** ({pkg2_version or 'unknown'})")
                    st.caption(f"License: {conflict.get('license_2', 'Unknown')}")

                if conflict.get("recommendation"):
                    st.caption(f"💡 Recommendation: {conflict.get('recommendation')}")

                st.markdown("---")

    st.markdown("## Dependency Overview")

    if known_packages:
        # Add status column with colored badges
        for pkg in known_packages:
            lic = pkg.get("License", "Unknown")
            if lic in ["MIT", "BSD-3-Clause", "BSD-2-Clause", "Apache-2.0", "ISC", "Zlib"]:
                pkg["Status"] = "🟢 Safe"
            elif lic == "Unknown":
                pkg["Status"] = "🟠 Unknown"
            else:
                pkg["Status"] = "🟡 Review"
        
        st.dataframe(
            known_packages,
            column_config={
                "Package": st.column_config.TextColumn("Package", width="medium"),
                "Version": st.column_config.TextColumn("Version", width="small"),
                "License": st.column_config.TextColumn("License", width="small"),
                "Status": st.column_config.TextColumn("Status", width="small"),
            },
            hide_index=True,
            use_container_width=True,
        )
    
    # Unknown licenses section for manual review
    if unknown_packages:
        with st.expander(f"Packages with Undetected Licenses ({len(unknown_packages)} need manual review)"):
            # Build table with reason
            unknown_table = []
            for pkg in unknown_packages:
                unknown_table.append({
                    "Package Name": pkg["Package"],
                    "Reason": "License not found in PyPI or npm registries"
                })
            
            st.dataframe(
                unknown_table,
                column_config={
                    "Package Name": st.column_config.TextColumn("Package Name", width="medium"),
                    "Reason": st.column_config.TextColumn("Reason", width="large"),
                },
                hide_index=True,
                use_container_width=True,
            )
            st.caption("These packages need manual license verification.")
    
    # Full dependency list
    with st.expander("Full Dependency List"):
        # Build full list with status
        full_deps = []
        for name, info in dependencies.items():
            lic = info.get("license", "Unknown")
            
            if lic == "Unknown":
                status = "🟠 Unknown"
            elif lic in ["MIT", "BSD-3-Clause", "BSD-2-Clause", "Apache-2.0", "ISC", "Zlib"]:
                status = "🟢 Safe"
            else:
                status = "🟡 Review"
            
            full_deps.append({
                "Package": name,
                "Version": info.get("version", "unknown"),
                "License": lic,
                "Status": status,
            })
        
        # Sort alphabetically
        full_deps = sorted(full_deps, key=lambda x: x["Package"].lower())
        
        st.dataframe(
            full_deps,
            column_config={
                "Package": st.column_config.TextColumn("Package", width="medium"),
                "Version": st.column_config.TextColumn("Version", width="small"),
                "License": st.column_config.TextColumn("License", width="small"),
                "Status": st.column_config.TextColumn("Status", width="small"),
            },
            hide_index=True,
            use_container_width=True,
            height=400,
        )

    errors = result.get("errors")
    if errors:
        with st.expander("View errors"):
            for err in errors:
                st.text(f"{err.get('step')}: {err.get('error')}")


if __name__ == "__main__":
    main()