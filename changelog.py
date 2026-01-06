import streamlit as st

def show_changelog():
    st.title("Changelog")
    st.caption("Release notes and version history.")

    st.markdown("---")

    # Current Version
    st.markdown("### v2.4.1 (Current)")
    st.markdown("""
    **January 6, 2026**
    - **UI/UX Reimagined**: Complete overhaul of the login interface for a cleaner, modern aesthetic.
    - **Logo Centering**: Fixed logo alignment on the login page for better visual balance.
    - **Code Consolidation**: Unified authentication and product management logic to reduce redundancy.
    - **Bug Fixes**: Resolved critical `st.button()` nesting issues within forms that caused application crashes.
    - **Performance Improvements**: Optimized image compression pipeline and product loading sequences.
    - **Admin Tools**: Added manual sync options for storage and inventory in a dedicated Admin section.
    """)

    st.markdown("---")

    st.markdown("### v2.4.0")
    st.markdown("""
    - **Supabase Caching**: Implemented a global caching layer for master product and inventory lists.
    - **Image Compression**: Integrated iterative JPEG compression to keep product images under 100KB.
    - **Adaptive Layouts**: Responsive navigation and form fields for mobile and wide-screen usage.
    - **Product Specifications**: Moved specifications editor to the bottom of the product form for better flow.
    """)

    st.markdown("---")

    st.markdown("### v2.3.0")
    st.markdown("""
    - **Inventory Sync**: Added automatic triggers to sync products from the catalog to the inventory table.
    - **Email Sender Integration**: Connected product images directly from storage to automated email templates.
    - **Security**: Added session timeouts and persistent authentication state.
    """)

    if st.button("← Back to Dashboard"):
        st.session_state["show_changelog"] = False
        st.rerun()
