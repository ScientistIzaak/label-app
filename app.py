import streamlit as st
import pandas as pd
import os
import uuid
from streamlit_extras.stylable_container import stylable_container

# ────────────────────────────────────────────────────────────────────
# GLOBAL CSS VARIABLES ONLY
# ────────────────────────────────────────────────────────────────────
st.markdown(
"""
<style>
:root {
  --primary-color: #3357a7;
  --primary-hover: #2a4593;
  --danger-color: #dc3545;
  --arrow-bg: rgba(51,87,167,0.1);
  --arrow-hover-bg: rgba(51,87,167,0.2);
}     
            
.st-emotion-cache-1m3gj4w {
    color: var(--primary-color);
}      

.st-emotion-cache-11v6ept {
    color: var(--primary-color);
}      
            
.st-key-st-key-false_btn button:hover {
    color: #fff;
}       

.st-key-st-key-true_btn button:hover {
    color: #fff;
}                 
            
.st-emotion-cache-4dbbln {
    color: var(--primary-color);
}
            
transition.style {
  --opacity: 1;          
}
            
.st-emotion-cache-z8vbw2:hover {
    border-color: var(--primary-color);
    color: #fff;
}           
.st-emotion-cache-z8vbw2:focus:not(:active) {
    border-color: currentColor;
    color: currentColor;                
}
            
.st-emotion-cache-9ajs8n {
    color: black;
}          

.st-emotion-cache-9ajs8n {
}         
</style>
"""
, unsafe_allow_html=True
)

# CONFIG
COMMENTS_FILE     = "data/comments.csv"
LABELS_FILE       = "data/labels.csv"
LABELS_WIDE_FILE  = "data/labels_wide.csv"
CATEGORIES        = ['Safety', 'Punctuality', 'Cleanliness', 'Driver Attitude']

# ────────────────────────────────────────────────────────────────────
# I/O FUNCTIONS
# ────────────────────────────────────────────────────────────────────
def load_comments():
    df = pd.read_csv(COMMENTS_FILE)
    if 'comment_id' not in df.columns:
        df['comment_id'] = [str(uuid.uuid4()) for _ in range(len(df))]
    return df


def load_persisted_labels():
    if not os.path.exists(LABELS_FILE):
        return pd.DataFrame(columns=["comment_id","comment_text","category","label"])
    return pd.read_csv(LABELS_FILE)


def save_labels_wide(long_df):
    # pivot long → wide: one row per comment, columns per category
    wide = (
        long_df
        .pivot_table(
            index=['comment_id', 'comment_text'],
            columns='category',
            values='label',
            aggfunc='first',
            fill_value=''
        )
        .reset_index()
    )
    # ensure all category columns exist
    for cat in CATEGORIES:
        if cat not in wide.columns:
            wide[cat] = ''
    # enforce column order
    wide = wide[['comment_id', 'comment_text'] + CATEGORIES]
    wide.to_csv(LABELS_WIDE_FILE, index=False)


def persist_labels(labels_map):
    persisted = load_persisted_labels()
    # remove old labels for current category
    persisted = persisted[persisted.category != st.session_state.category]
    comments = load_comments()
    records = []
    for cid, lbl in labels_map.items():
        text = comments.loc[comments.comment_id == cid, 'comment_text'].iat[0]
        records.append({
            'comment_id': cid,
            'comment_text': text,
            'category': st.session_state.category,
            'label': lbl
        })
    out = pd.concat([persisted, pd.DataFrame(records)], ignore_index=True)
    # write long format
    out.to_csv(LABELS_FILE, index=False)
    # write wide format
    save_labels_wide(out)

# ────────────────────────────────────────────────────────────────────
# SESSION STATE DEFAULTS
# ────────────────────────────────────────────────────────────────────
for key, val in {
    'step': 'setup',
    'category': None,
    'target_true': 0,
    'index': 0,
    'labels_map': {},
    'show_finish_modal': False,
    'show_congrats_modal': False
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

# ────────────────────────────────────────────────────────────────────
# NAVIGATION
# ────────────────────────────────────────────────────────────────────
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Labeling", "Summary"] )
comments_df  = load_comments()
persisted_df = load_persisted_labels()

if page == "Labeling":
    # Congratulations popup when true-label goal reached
    if st.session_state.show_congrats_modal:
        st.title("🎉 Congratulations!")
        st.write(f"You have reached your goal of **{st.session_state.target_true}** true labels!")
        if st.button("🏠 Home"):
            st.session_state.step = 'setup'
            st.session_state.labels_map = {}
            st.session_state.show_congrats_modal = False
            st.rerun()
        st.stop()

    # Finish popup
    if st.session_state.show_finish_modal:
        true_count  = sum(v == 1 for v in st.session_state.labels_map.values())
        false_count = sum(v == 0 for v in st.session_state.labels_map.values())
        completed   = true_count + false_count
        target_true = st.session_state.target_true
        st.title("🏁 Labeling Complete")
        st.write(f"✅ True answered: **{true_count}**")
        st.write(f"❌ False answered: **{false_count}**")
        st.write(f"🔢 Total answered: **{completed}**")
        st.write(f"🎯 Goal for true labels: **{target_true}**")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🏠 Home"):
                st.session_state.step = 'setup'
                st.session_state.labels_map = {}
                st.session_state.show_finish_modal = False
                st.rerun()
        with c2:
            if st.button("❌ Cancel"):
                st.session_state.show_finish_modal = False
                st.rerun()
        st.stop()

    # Setup screen
    if st.session_state.step == 'setup':
        st.title("🔧 Labeling Setup")
        st.session_state.category    = st.selectbox("Select Category", CATEGORIES)
        st.session_state.target_true = st.number_input("Target True Labels", min_value=1, value=10)
        if st.button("Start Labeling"):
            st.session_state.labels_map = {}
            st.session_state.index      = 0
            st.session_state.step       = 'labeling'
            st.rerun()
    else:
        # Labeling screen
        st.title(f"Category: {st.session_state.category}")
        true_count  = sum(v == 1 for v in st.session_state.labels_map.values())
        false_count = sum(v == 0 for v in st.session_state.labels_map.values())
        # Trigger congrats when goal met
        if true_count >= st.session_state.target_true and not st.session_state.show_congrats_modal:
            st.session_state.show_congrats_modal = True
            st.rerun()
        pct = int(true_count / max(1, st.session_state.target_true) * 100)
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"🔥 **{pct}%** of target")
        c2.markdown(f"✅ **True:** {true_count}")
        c3.markdown(f"❌ **False:** {false_count}")
        c4.markdown(" ")
        st.progress(true_count / max(1, st.session_state.target_true))
        done_ids = set(persisted_df[persisted_df.category == st.session_state.category].comment_id)
        skip_ids = done_ids | set(st.session_state.labels_map.keys())
        pool     = comments_df[~comments_df.comment_id.isin(skip_ids)].reset_index(drop=True)
        if pool.empty:
            st.warning("No more unlabeled comments." )
            st.stop()
        idx = st.session_state.index = max(0, min(st.session_state.index, len(pool)-1))
        row = pool.iloc[idx]; cid = row.comment_id
        cols = st.columns([1,8,1])
        with cols[0]:
            if idx > 0 and st.button("←"):
                st.session_state.index -= 1
                st.rerun()
        with cols[1]:
            st.markdown(
                f"<div style='padding:1rem; background:#f9f9f9; "
                f"border-left:5px solid var(--primary-color); "
                f"border-radius:0.5rem; margin-bottom:1.5rem; color:#000 !important;'>"
                f"{row.comment_text}</div>", unsafe_allow_html=True)
        with cols[2]:
            if idx < len(pool)-1 and st.button("→"):
                st.session_state.index += 1
                st.rerun()
        fcol, tcol = st.columns(2)
        with fcol:
            with stylable_container(key='false_btn', css_styles="""
                button {width:100%;padding:1rem;background:var(--danger-color);color:#fff;border:none;border-radius:0.5rem;transition:transform 0.2s;}button:hover {transform:scale(1.05);}"""):
                if st.button("❌ FALSE"):
                    st.session_state.labels_map[cid] = 0
                    persist_labels(st.session_state.labels_map)
                    st.rerun()
        with tcol:
            with stylable_container(key='true_btn', css_styles="""
                button {width:100%;padding:1rem;background:var(--primary-color);color:#fff;border:none;border-radius:0.5rem;transition:transform 0.2s;}button:hover {transform:scale(1.05); color: #fff}"""):
                if st.button("✅ TRUE"):
                    st.session_state.labels_map[cid] = 1
                    persist_labels(st.session_state.labels_map)
                    st.rerun()
        st.markdown("---")
        with stylable_container(key='finish', css_styles="""
            button {display:block;margin:1rem auto;width:8rem;height:3rem;background:transparent;border:2px solid var(--primary-color);border-radius:1rem;color:var(--primary-color);font-size:1.25rem;font-weight:600;transition:transform 0.2s;}button:hover {transform:scale(1.1);}"""):
            if st.button("Finish"):
                st.session_state.show_finish_modal = True
                st.rerun()
else:
    st.title("Labeling Summary by Category")
    df = load_persisted_labels()
    rows = []
    for cat in CATEGORIES:
        sub = df[df.category == cat]
        rows.append({
            'Category':    cat,
            '✅ True':     (sub.label == 1).sum(),
            '❌ False':    (sub.label == 0).sum(),
            '🔢 Labeled':  len(sub),
            '🕳️ Unlabeled': len(comments_df) - len(sub)
        })
    summary_df = pd.DataFrame(rows)
    totals = {
        'Category':     'Total',
        '✅ True':      summary_df['✅ True'].sum(),
        '❌ False':     summary_df['❌ False'].sum(),
        '🔢 Labeled':   summary_df['🔢 Labeled'].sum(),
        '🕳️ Unlabeled': summary_df['🕳️ Unlabeled'].sum()
    }
    summary_df = pd.concat([summary_df, pd.DataFrame([totals])], ignore_index=True)
    st.dataframe(summary_df, use_container_width=True)
