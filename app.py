def chip_row(label, options, selected, multi=False, key_prefix=""):
    st.write(f"### {label}")

    # Container for pills
    pill_container = st.container()

    # Build clickable pills using query params
    query_params = st.experimental_get_query_params()

    clicked_value = query_params.get(f"{key_prefix}_clicked", [None])[0]

    # If a pill was clicked, update selection
    if clicked_value in options:
        if multi:
            if clicked_value in selected:
                selected.remove(clicked_value)
            else:
                selected.append(clicked_value)
        else:
            selected.clear()
            selected.append(clicked_value)

        # Clear the click param so it doesn't persist
        st.experimental_set_query_params()

    # Render pills
    pill_html = "<div style='display:flex;flex-wrap:wrap;gap:6px;'>"

    for opt in options:
        is_selected = opt in selected

        bg = "#4CAF50" if is_selected else "#FFFFFF"
        color = "#FFFFFF" if is_selected else "#555555"
        shadow = "box-shadow:0px 1px 3px rgba(0,0,0,0.15);" if not is_selected else ""

        pill_html += f"""
        <a href='?{key_prefix}_clicked={opt}' style='text-decoration:none;'>
            <div style="
                background:{bg};
                color:{color};
                padding:8px 14px;
                border-radius:10px;
                font-size:16px;
                {shadow}
            ">
                {opt}
            </div>
        </a>
        """

    pill_html += "</div>"

    pill_container.markdown(pill_html, unsafe_allow_html=True)

    return selected