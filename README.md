import random
import time

import streamlit as st

# ============================================================
# 基本設定
# ============================================================
st.set_page_config(
    page_title="通信障害 探偵ゲーム 🕵️‍♂️📡",
    page_icon="📡",
    layout="centered",
)

# ============================================================
# データ定義
# ============================================================

# --- ステージ1: ネットワークの経路情報 ---
NET_ORDER = ["phone", "router", "isp", "dns", "webserver"]
NET_INFO = {
    "phone": {"emoji": "📱", "label": "自分のスマホ"},
    "router": {"emoji": "📶", "label": "家のルーター"},
    "isp": {"emoji": "🏢", "label": "プロバイダ"},
    "dns": {"emoji": "📖", "label": "DNSサーバー"},
    "webserver": {"emoji": "🌍", "label": "Webサーバー"},
}
NET_FAULT_CANDIDATES = ["router", "isp", "dns", "webserver"]

NET_TESTS = {
    "ping_router": {
        "name": "① ルーターまでの接続を確認 (Ping)",
        "path": ["router"],
        "desc": "自宅内の入り口であるルーターまで、まず声が届くか確認するよ。",
    },
    "ping_ip": {
        "name": "② WebサーバーのIPアドレス(数字の住所)へ接続を確認 (Ping)",
        "path": ["router", "isp", "webserver"],
        "desc": "住所録(DNS)を使わず、最初から数字の住所(IPアドレス)を直接指定して届くか確認するよ。",
    },
    "ping_url": {
        "name": "③ WebサーバーのURL(文字の住所)へ接続を確認 (DNS経由のPing)",
        "path": ["router", "isp", "dns", "webserver"],
        "desc": "普段ブラウザで使う『文字の住所(URL)』でアクセスするよ。まずDNSで住所を調べてから届くか確認するんだ。",
    },
}

NET_EXPLANATIONS = {
    "router": (
        "🔴「①ルーターまでのPing」が失敗していたら、それが決定打だよ！\n\n"
        "スマホから一番近い『家庭内ネットワークの入口』であるルーターの時点で応答が返ってこないということは、"
        "その先のプロバイダやDNS、Webサーバーを調べるまでもなく、**自宅内の設備(ルーター)自体に問題がある**と判断できるんだ。"
        "一番手前の関門で止まっている＝それより奥は調べる必要がない、というのが切り分けの基本だよ。"
    ),
    "isp": (
        "「①ルーターまでのPing」は🟢成功するのに、「②IPアドレスへのPing」が🔴失敗する、というのがカギだよ。\n\n"
        "ルーターまでは無事に届いている＝**自宅内のネットワークは正常**。でもそこから外に出た直後(プロバイダ)で止まっている。"
        "つまり原因は自宅の中ではなく、**プロバイダ(回線事業者)側**にあると考えられるね。"
    ),
    "dns": (
        "「②IPアドレスへのPing」は🟢成功するのに、「③URLへのPing」だけ🔴失敗する、というのが決め手だよ。\n\n"
        "数字の住所(IP)で直接行けば届くのに、文字の住所(URL)からだと届かない…ということは、"
        "**道順(ネットワーク経路)自体には問題がなく、住所を変換するDNSの仕組みだけが壊れている**とわかるね。"
    ),
    "webserver": (
        "「①ルーターまでのPing」も🟢、「③URLへのPing」で調べても**DNSまでは通っている**のに、"
        "肝心の「②IPアドレスへのPing」がWebサーバー手前で🔴失敗する、というのがポイントだよ。\n\n"
        "経路(ルーター・プロバイダ・DNS)はすべて正常なので、原因はネットワークではなく、"
        "**Webサーバー本体(相手側の機器)がダウンしている**可能性が高いんだ。"
    ),
}

NET_ANSWER_CHOICES = {
    "router": "📶 家のルーター",
    "isp": "🏢 プロバイダ",
    "dns": "📖 DNSサーバー",
    "webserver": "🌍 Webサーバー本体",
}

# --- ステージ2: 日常トラブル(お風呂のお湯)情報 ---
HOME_ORDER = ["shower", "boiler", "gas_valve", "gas_company"]
HOME_INFO = {
    "shower": {"emoji": "🚿", "label": "シャワーヘッド・お風呂の蛇口(個別設備)"},
    "boiler": {"emoji": "🔥", "label": "給湯器(ボイラー)"},
    "gas_valve": {"emoji": "⛽", "label": "ガスの元栓・メーター"},
    "gas_company": {"emoji": "🏭", "label": "ガス会社(地域の供給)"},
}

HOME_TESTS = {
    "check_kitchen": {
        "name": "🚰 まずはキッチンの水がお湯になるか確認する",
        "desc": "お風呂『だけ』の問題なのか、家全体の問題なのかを切り分けるよ。ネットワークで言う『他の機器でも同じ症状か確認する』のと同じ考え方だね。",
    },
    "check_boiler": {
        "name": "🔥 給湯器(ボイラー)の運転ランプ・エラー表示を確認する",
        "desc": "家の中の設備そのものが壊れていないか、直接チェックするよ。ネットワークで言う『ルーターの様子を見る』のと同じ考え方。",
    },
    "check_valve": {
        "name": "⛽ 家の元栓(ガスメーター)を見る",
        "desc": "自宅とガス会社の『境界』に問題がないか確認するよ。ネットワークで言う『プロバイダとの接続を疑う』のと同じ考え方。",
    },
    "check_company": {
        "name": "🏭 ガス会社の公式サイトやSNSで地域の障害情報を確認する",
        "desc": "自分の家の外、地域全体の問題ではないか確認するよ。ネットワークで言う『外部のサーバー側を疑う』のと同じ考え方。",
    },
}

HOME_RESULT_TEXT = {
    "shower": {
        "check_kitchen": ("success", "🟢 キッチンはちゃんとお湯が出た！ → 家全体は正常みたい。"),
        "check_boiler": ("success", "🟢 給湯器のランプは正常点灯。エラー表示なし。"),
        "check_valve": ("success", "🟢 元栓もメーターも正常。ガスはちゃんと来ている。"),
        "check_company": ("success", "🟢 ガス会社からの障害情報は見当たらない。"),
    },
    "boiler": {
        "check_kitchen": ("fail", "🔴 キッチンもお湯が出ない…家全体でお湯が使えないみたい。"),
        "check_boiler": ("fail", "🔴 給湯器にエラーランプが点滅している！これが怪しい。"),
        "check_valve": ("success", "🟢 元栓・メーターは正常。ガスはちゃんと来ている。"),
        "check_company": ("success", "🟢 ガス会社からの障害情報は見当たらない。"),
    },
    "gas_valve": {
        "check_kitchen": ("fail", "🔴 キッチンもお湯が出ない…家全体でお湯が使えないみたい。"),
        "check_boiler": ("success", "🟢 給湯器自体は正常起動しているが、ガスが来ていない様子。"),
        "check_valve": ("fail", "🔴 元栓が閉まっている？メーターにエラー表示が出ている！"),
        "check_company": ("success", "🟢 ガス会社からの障害情報は見当たらない。"),
    },
    "gas_company": {
        "check_kitchen": ("fail", "🔴 キッチンもお湯が出ない…家全体でお湯が使えないみたい。"),
        "check_boiler": ("success", "🟢 給湯器自体は正常起動しているが、ガスが来ていない様子。"),
        "check_valve": ("success", "🟢 元栓・メーターも異常なし。"),
        "check_company": ("fail", "🔴 「〇〇地域でガス供給の緊急停止」というお知らせを発見！"),
    },
}

HOME_EXPLANATIONS = {
    "shower": (
        "キッチンではお湯が出るのに、お風呂『だけ』出ない。つまり**家全体は正常**で、"
        "問題は**お風呂のシャワーヘッドや蛇口という個別の設備**に絞り込めるね。"
        "ネットワークで言えば、ルーターより先は全部正常なのに1台のスマホだけ調子が悪い、という状況とそっくりだ。"
    ),
    "boiler": (
        "キッチンも含めて家全体でお湯が出ず、給湯器にエラーランプが出ていた。"
        "でもガスの元栓やガス会社は正常。つまり**自宅内の設備(給湯器)そのもの**に原因があるとわかるね。"
        "ネットワークで言えば『家庭内ネットワーク(ルーター)』の不具合と同じ位置づけだよ。"
    ),
    "gas_valve": (
        "家全体でお湯が出ず、給湯器自体は正常なのに、元栓・メーターに異常があった。"
        "つまり原因は**家とガス会社の『境界』部分**にあるとわかるね。"
        "ネットワークで言えば『プロバイダとの接続がおかしい』状況と同じ位置づけだよ。"
    ),
    "gas_company": (
        "家全体でお湯が出ず、給湯器も元栓も正常なのに、ガス会社から地域障害のお知らせが出ていた。"
        "つまり原因は**自分の家の中ではなく、外部(ガス会社側)**にあるとわかるね。"
        "ネットワークで言えば『Webサーバー側がダウンしている』状況と同じ位置づけだよ。"
    ),
}

HOME_ANSWER_CHOICES = {
    "shower": "🚿 シャワーヘッド・蛇口(個別設備)",
    "boiler": "🔥 給湯器(ボイラー)",
    "gas_valve": "⛽ ガスの元栓・メーター",
    "gas_company": "🏭 ガス会社(地域の供給)",
}


# ============================================================
# セッション状態の初期化
# ============================================================
def init_state():
    if "fault1" not in st.session_state:
        st.session_state.fault1 = random.choice(NET_FAULT_CANDIDATES)
    if "history1" not in st.session_state:
        st.session_state.history1 = []
    if "quiz1_answered" not in st.session_state:
        st.session_state.quiz1_answered = False
    if "quiz1_correct" not in st.session_state:
        st.session_state.quiz1_correct = False
    if "attempts1" not in st.session_state:
        st.session_state.attempts1 = 0
    if "stage1_cleared" not in st.session_state:
        st.session_state.stage1_cleared = False

    if "fault2" not in st.session_state:
        st.session_state.fault2 = random.choice(HOME_ORDER)
    if "checked2" not in st.session_state:
        st.session_state.checked2 = {}
    if "quiz2_answered" not in st.session_state:
        st.session_state.quiz2_answered = False
    if "quiz2_correct" not in st.session_state:
        st.session_state.quiz2_correct = False
    if "attempts2" not in st.session_state:
        st.session_state.attempts2 = 0
    if "stage2_cleared" not in st.session_state:
        st.session_state.stage2_cleared = False


def reset_stage1(full=False):
    st.session_state.fault1 = random.choice(NET_FAULT_CANDIDATES)
    st.session_state.history1 = []
    st.session_state.quiz1_answered = False
    st.session_state.quiz1_correct = False
    st.session_state.attempts1 = 0
    if full:
        st.session_state.stage1_cleared = False


def reset_stage2():
    st.session_state.fault2 = random.choice(HOME_ORDER)
    st.session_state.checked2 = {}
    st.session_state.quiz2_answered = False
    st.session_state.quiz2_correct = False
    st.session_state.attempts2 = 0


def reset_all():
    reset_stage1(full=True)
    reset_stage2()
    st.session_state.stage2_cleared = False


# ============================================================
# ステージ1 用の補助関数
# ============================================================
def compute_known_status():
    """これまでの調査結果から、各ノードの既知の状態(unknown/ok/fail)を集計する"""
    status = {node: "unknown" for node in NET_ORDER}
    status["phone"] = "ok"  # 自分のスマホは常に正常(出発点)
    for entry in st.session_state.history1:
        for node, ok in entry["results"]:
            status[node] = "ok" if ok else "fail"
    return status


def render_network_diagram():
    st.markdown("#### 🗺️ 現在の通信経路")
    known = compute_known_status()
    icon_map = {"ok": "🟢", "fail": "🔴", "unknown": "⚪"}
    cols = st.columns(len(NET_ORDER))
    for i, node in enumerate(NET_ORDER):
        info = NET_INFO[node]
        with cols[i]:
            st.markdown(f"**{info['emoji']}**")
            st.caption(info["label"])
            if node != "phone":
                st.markdown(icon_map[known[node]])
    st.caption("⚪ 未調査　🟢 応答あり(正常)　🔴 応答なし(異常)")


def run_network_test(test_key):
    test = NET_TESTS[test_key]
    path = test["path"]
    fault = st.session_state.fault1

    st.write(f"🔍 **{test['name']}** を実行中…")
    progress_bar = st.progress(0)
    status_area = st.empty()

    results = []
    success = True
    total = len(path)
    for i, node in enumerate(path):
        time.sleep(0.35)
        pct = int(((i + 1) / total) * 100)
        info = NET_INFO[node]
        if node == fault:
            progress_bar.progress(pct)
            status_area.error(f"{info['emoji']} {info['label']} … 🔴 応答なし！ここで通信が跳ね返されました。")
            results.append((node, False))
            success = False
            break
        else:
            progress_bar.progress(pct)
            status_area.info(f"{info['emoji']} {info['label']} … 🟢 応答OK、次へ進みます。")
            results.append((node, True))

    time.sleep(0.2)
    if success:
        st.success(f"🎉 「{test['name']}」は最後まで無事に届きました！(🟢 成功)")
    else:
        st.error(f"💥 「{test['name']}」は途中で失敗しました。(🔴 失敗)")

    st.session_state.history1.append(
        {"name": test["name"], "results": results, "success": success}
    )


def render_history1():
    if not st.session_state.history1:
        st.info("まだ調査していないよ。上のボタンから調査ツールを実行してみよう！")
        return
    st.markdown("#### 📋 これまでの調査ログ")
    for idx, entry in enumerate(reversed(st.session_state.history1), start=1):
        icon = "🟢 成功" if entry["success"] else "🔴 失敗"
        path_str = " → ".join(
            f"{NET_INFO[n]['emoji']}{'🟢' if ok else '🔴'}" for n, ok in entry["results"]
        )
        st.write(f"{len(st.session_state.history1) - idx + 1}. **{entry['name']}** ： {icon}　｜　{path_str}")


# ============================================================
# ステージ2 用の補助関数
# ============================================================
def run_home_check(check_key):
    fault = st.session_state.fault2
    status, text = HOME_RESULT_TEXT[fault][check_key]
    st.session_state.checked2[check_key] = (status, text)
    if status == "success":
        st.success(text)
    else:
        st.error(text)


def render_home_diagram():
    st.markdown("#### 🏠 給湯の仕組み(かんたん図)")
    cols = st.columns(len(HOME_ORDER))
    for i, node in enumerate(HOME_ORDER):
        info = HOME_INFO[node]
        with cols[i]:
            st.markdown(f"**{info['emoji']}**")
            st.caption(info["label"])
    st.caption("🚿 蛇口 → 🔥 給湯器 → ⛽ 元栓 → 🏭 ガス会社　の順につながっているよ")


def render_checked_log():
    if not st.session_state.checked2:
        st.info("まだ何も確認していないよ。上のボタンから確認してみよう！")
        return
    st.markdown("#### 📋 これまでの確認ログ")
    for key, (status, text) in st.session_state.checked2.items():
        name = HOME_TESTS[key]["name"]
        st.write(f"・**{name}**\n　→ {text}")


# ============================================================
# メイン画面
# ============================================================
init_state()

st.title("📡 通信障害 探偵ゲーム")
st.caption("情報Ⅰ｜ネットワークのトラブルシューティングを体験しよう")

with st.sidebar:
    st.header("🎮 メニュー")
    st.write(f"ステージ1 挑戦回数：**{st.session_state.attempts1}** 回")
    if st.session_state.stage1_cleared:
        st.write(f"ステージ2 挑戦回数：**{st.session_state.attempts2}** 回")
    st.divider()
    if st.button("🔄 最初から全部やり直す", use_container_width=True):
        reset_all()
        st.rerun()
    st.divider()
    st.markdown(
        "**このアプリで学ぶこと**\n\n"
        "通信トラブルが起きたとき、経路を『区切って』一つずつ調べることで、"
        "原因がどこにあるかを論理的に絞り込む考え方＝**切り分け**を体験します。"
    )

st.divider()

# ---------------- ステージ1 ----------------
st.header("🕵️ ステージ1：通信障害を突き止めろ！")
st.write(
    "あなたの家のどこかで通信トラブルが発生しています。3つの調査ツールを使って、"
    "どこで通信が止まっているのかを突き止めよう！(ツールは何度でも使えるよ)"
)

render_network_diagram()
st.write("")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button(NET_TESTS["ping_router"]["name"], use_container_width=True):
        with st.container(border=True):
            st.caption(NET_TESTS["ping_router"]["desc"])
            run_network_test("ping_router")
with col2:
    if st.button(NET_TESTS["ping_ip"]["name"], use_container_width=True):
        with st.container(border=True):
            st.caption(NET_TESTS["ping_ip"]["desc"])
            run_network_test("ping_ip")
with col3:
    if st.button(NET_TESTS["ping_url"]["name"], use_container_width=True):
        with st.container(border=True):
            st.caption(NET_TESTS["ping_url"]["desc"])
            run_network_test("ping_url")

st.write("")
render_history1()

st.write("")
st.subheader("🤔 推理タイム：障害の原因はどこ？")
answer1 = st.radio(
    "調査結果から、障害箇所を1つ選んでね",
    options=list(NET_ANSWER_CHOICES.keys()),
    format_func=lambda k: NET_ANSWER_CHOICES[k],
    key="answer1_radio",
    horizontal=False,
)

if st.button("✅ この場所が原因だと思う！回答する", type="primary"):
    st.session_state.attempts1 += 1
    st.session_state.quiz1_answered = True
    st.session_state.quiz1_correct = answer1 == st.session_state.fault1

if st.session_state.quiz1_answered:
    if st.session_state.quiz1_correct:
        st.success("🎉 正解！お見事、名探偵だね！")
        st.info(NET_EXPLANATIONS[st.session_state.fault1])
        st.session_state.stage1_cleared = True
        st.balloons()
    else:
        st.error("😵 残念、不正解…もう一度調査結果を見直してみよう。")
        st.warning(
            "ヒント：どのツールが🔴失敗して、どのツールが🟢成功したかを比べてみよう。"
            "『どこまでは届いたか』が一番大事な手がかりだよ。"
        )

if st.session_state.stage1_cleared:
    st.success("🏆 ステージ1クリア！下のボタンで新しいパターンにも挑戦できるよ。")
    if st.button("🔁 別の障害パターンでもう一度挑戦する"):
        reset_stage1(full=False)
        st.rerun()

st.divider()

# ---------------- ステージ2 ----------------
if not st.session_state.stage1_cleared:
    st.header("🔒 ステージ2：日常トラブル応用編")
    st.info("ステージ1をクリアすると解放されるよ。まずはネットワークの障害を突き止めよう！")
else:
    st.header("🛁 ステージ2：日常トラブル応用編")
    st.write(
        "ネットワークで学んだ『切り分け』の考え方は、日常生活のトラブルにもそのまま使えるよ。"
        "さっそく試してみよう！"
    )
    st.warning("😱 大変！お風呂からお湯が出ない！さて、どうやって原因を切り分ける？")

    render_home_diagram()
    st.write("")

    hcol1, hcol2 = st.columns(2)
    hcol3, hcol4 = st.columns(2)
    home_cols = {
        "check_kitchen": hcol1,
        "check_boiler": hcol2,
        "check_valve": hcol3,
        "check_company": hcol4,
    }
    for key, col in home_cols.items():
        with col:
            if st.button(HOME_TESTS[key]["name"], use_container_width=True, key=f"btn_{key}"):
                with st.container(border=True):
                    st.caption(HOME_TESTS[key]["desc"])
                    run_home_check(key)

    st.write("")
    render_checked_log()

    st.write("")
    st.subheader("🤔 推理タイム：お湯が出ない原因はどこ？")
    answer2 = st.radio(
        "確認結果から、原因を1つ選んでね",
        options=list(HOME_ANSWER_CHOICES.keys()),
        format_func=lambda k: HOME_ANSWER_CHOICES[k],
        key="answer2_radio",
    )

    if st.button("✅ この場所が原因だと思う！回答する", type="primary", key="submit2"):
        st.session_state.attempts2 += 1
        st.session_state.quiz2_answered = True
        st.session_state.quiz2_correct = answer2 == st.session_state.fault2

    if st.session_state.quiz2_answered:
        if st.session_state.quiz2_correct:
            st.success("🎉 正解！日常のトラブルでも見事に切り分けられたね！")
            st.info(HOME_EXPLANATIONS[st.session_state.fault2])
            st.session_state.stage2_cleared = True
            st.balloons()
        else:
            st.error("😵 残念、不正解…確認結果をもう一度比べてみよう。")
            st.warning(
                "ヒント：『家全体の問題か、個別の設備だけの問題か』をまず切り分けるのがコツだよ。"
            )

    if st.session_state.stage2_cleared:
        st.success("🏆 ステージ2クリア！おめでとう！")
        st.markdown(
            "### 🎓 学んだこと\n"
            "ネットワークのトラブルも、お風呂のトラブルも、考え方は同じだったね。\n\n"
            "- 経路を **区切って(分割して)**、一つずつ検証する\n"
            "- 『どこまでは正常で、どこから異常か』を手がかりに絞り込む\n"
            "- これが情報の世界でもくらしの中でも使える"
            "「切り分け」というエンジニアリングの考え方なんだ！"
        )
        if st.button("🔁 別のパターンでもう一度挑戦する", key="retry2"):
            reset_stage2()
            st.rerun()