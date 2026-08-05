import random
import time
import streamlit as st

# ============================================================
# 基本設定とCSSアニメーション (Webアプリ設計の条件に従い外部ファイル化しない)
# ============================================================
st.set_page_config(
    page_title="通信障害 探偵ゲーム 🕵️‍♂️📡",
    page_icon="📡",
    layout="centered",
)

st.markdown("""
<style>
@keyframes flash-red {
    0% { background-color: transparent; }
    50% { background-color: #ffcccc; border-radius: 8px; box-shadow: 0 0 10px red;}
    100% { background-color: transparent; }
}
.flashing {
    animation: flash-red 1s infinite;
    padding: 10px;
    text-align: center;
}
.normal-node {
    padding: 10px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# データ定義 (ステージ1)
# ============================================================
NET_ORDER = ["phone", "router", "isp", "dns", "webserver"]
NET_INFO = {
    "phone": {"emoji": "📱", "label": "スマホ"},
    "router": {"emoji": "📶", "label": "ルーター"},
    "isp": {"emoji": "🏢", "label": "プロバイダ"},
    "dns": {"emoji": "📖", "label": "DNS"},
    "webserver": {"emoji": "🌍", "label": "Webサーバー"},
}
NET_FAULT_CANDIDATES = ["router", "isp", "dns", "webserver"]

NET_TESTS = {
    "ping_router": {
        "name": "① ルーターまでの接続を確認",
        "path": ["router"],
        "desc": "自宅内の入り口であるルーターまで、まず声が届くか確認するよ。",
    },
    "ping_ip": {
        "name": "② IPアドレス(数字の住所)へ接続",
        "path": ["router", "isp", "webserver"],
        "desc": "住所録(DNS)を使わず、最初から数字の住所(IPアドレス)を直接指定して届くか確認するよ。",
    },
    "ping_url": {
        "name": "③ URL(文字の住所)へ接続",
        "path": ["router", "isp", "dns", "webserver"],
        "desc": "普段ブラウザで使う『文字の住所(URL)』でアクセスするよ。まずDNSを経由するよ。",
    },
}

NET_EXPLANATIONS = {
    "router": "🔴「①ルーターまでのPing」が失敗していたら、それが決定打！\nスマホから一番近い『家庭内ネットワークの入口』で応答がないので、自宅内の設備(ルーター)自体に問題があると判断できるんだ。",
    "isp": "「①ルーターまで」は🟢成功するのに、「②IPアドレスへ」が🔴失敗するのがカギ。\n自宅内のネットワークは正常。外に出た直後で止まっているのでプロバイダ(回線事業者)側に原因があるね。",
    "dns": "「②IPアドレスへ」は🟢成功するのに、「③URLへ」だけ🔴失敗するのが決め手。\n数字の住所なら届くのに、文字の住所だと届かない＝住所を変換するDNSの仕組みだけが壊れているとわかるね。",
    "webserver": "経路(ルーター・プロバイダ・DNS)はすべて正常(🟢)なのに、肝心の「②IPアドレスへ」がWebサーバー手前で🔴失敗する。\n相手側の機器(Webサーバー本体)がダウンしている可能性が高いんだ。",
}

NET_ANSWER_CHOICES = {
    "router": "📶 家のルーター",
    "isp": "🏢 プロバイダ",
    "dns": "📖 DNSサーバー",
    "webserver": "🌍 Webサーバー本体",
}

# ============================================================
# データ定義 (ステージ2: 4つのパターン)
# ============================================================
SCENARIOS = {
    "gas": {
        "title": "お風呂のお湯が出ない！(ガス)",
        "order": ["client", "local", "gateway", "external"],
        "info": {
            "client": {"emoji": "🚿", "label": "シャワー設備"},
            "local": {"emoji": "🔥", "label": "給湯器"},
            "gateway": {"emoji": "⛽", "label": "ガスの元栓"},
            "external": {"emoji": "🏭", "label": "ガス会社"},
        },
        "tests": {
            "test1": {"name": "🚰 キッチンの水がお湯になるか確認", "desc": "家全体か、お風呂だけの問題か切り分けるよ。"},
            "test2": {"name": "🔥 給湯器の運転ランプを確認", "desc": "家の中の設備そのものが壊れていないか確認するよ。"},
            "test3": {"name": "⛽ ガスメーター(元栓)を見る", "desc": "自宅と外部の『境界』に問題がないか確認するよ。"},
            "test4": {"name": "🏭 ガス会社の障害情報を確認", "desc": "地域全体の問題ではないか確認するよ。"},
        },
        "results": {
            "client": {"test1": ("success", "🟢 キッチンはお湯が出た！"), "test2": ("success", "🟢 給湯器は正常。"), "test3": ("success", "🟢 元栓も正常。"), "test4": ("success", "🟢 障害情報なし。")},
            "local": {"test1": ("fail", "🔴 キッチンもお湯が出ない。"), "test2": ("fail", "🔴 給湯器にエラーランプ！"), "test3": ("success", "🟢 元栓は正常。"), "test4": ("success", "🟢 障害情報なし。")},
            "gateway": {"test1": ("fail", "🔴 キッチンもお湯が出ない。"), "test2": ("success", "🟢 給湯器は起動している。"), "test3": ("fail", "🔴 元栓が閉まっている/メーター異常！"), "test4": ("success", "🟢 障害情報なし。")},
            "external": {"test1": ("fail", "🔴 キッチンもお湯が出ない。"), "test2": ("success", "🟢 給湯器は起動している。"), "test3": ("success", "🟢 元栓は正常。"), "test4": ("fail", "🔴 地域でガス供給停止のお知らせ！")},
        },
        "explanations": {
            "client": "キッチンでお湯が出るなら家全体は正常。原因はお風呂のシャワー設備(個別設備)だね。",
            "local": "家全体でお湯が出ず、給湯器にエラー。原因は自宅内の設備(給湯器)そのものだね。",
            "gateway": "給湯器は正常なのにガスが来ていない。原因は家と外部の境界(元栓・メーター)だね。",
            "external": "家側の設備はすべて正常。原因は外部(ガス会社側)の地域障害だね。",
        },
        "choices": {"client": "🚿 シャワー設備(個別)", "local": "🔥 給湯器(ボイラー)", "gateway": "⛽ ガスの元栓", "external": "🏭 ガス会社"},
    },
    "electricity": {
        "title": "デスクライトがつかない！(電気)",
        "order": ["client", "local", "gateway", "external"],
        "info": {
            "client": {"emoji": "💡", "label": "デスクライト"},
            "local": {"emoji": "🔌", "label": "部屋のコンセント"},
            "gateway": {"emoji": "⚡", "label": "家のブレーカー"},
            "external": {"emoji": "🏢", "label": "電力会社"},
        },
        "tests": {
            "test1": {"name": "📱 スマホの充電器を挿してみる", "desc": "ライトだけの問題か、コンセントの問題か切り分けるよ。"},
            "test2": {"name": "💡 別の部屋の電気をつける", "desc": "家全体の問題か、その部屋だけの問題か切り分けるよ。"},
            "test3": {"name": "⚡ 家のブレーカーを確認", "desc": "自宅と外部の『境界』に落ちているスイッチがないか確認するよ。"},
            "test4": {"name": "🏢 電力会社の停電情報を確認", "desc": "地域全体の問題ではないか確認するよ。"},
        },
        "results": {
            "client": {"test1": ("success", "🟢 スマホは充電できた！"), "test2": ("success", "🟢 別の部屋の電気はつく。"), "test3": ("success", "🟢 ブレーカーは落ちていない。"), "test4": ("success", "🟢 停電情報なし。")},
            "local": {"test1": ("fail", "🔴 スマホも充電できない。"), "test2": ("success", "🟢 別の部屋の電気はつく。"), "test3": ("success", "🟢 メインのブレーカーは正常。"), "test4": ("success", "🟢 停電情報なし。")},
            "gateway": {"test1": ("fail", "🔴 スマホも充電できない。"), "test2": ("fail", "🔴 家中すべての電気がつかない。"), "test3": ("fail", "🔴 メインブレーカーが落ちている！"), "test4": ("success", "🟢 停電情報なし。")},
            "external": {"test1": ("fail", "🔴 スマホも充電できない。"), "test2": ("fail", "🔴 家中すべての電気がつかない。"), "test3": ("success", "🟢 ブレーカーは落ちていない。"), "test4": ("fail", "🔴 地域で大規模停電のお知らせ！")},
        },
        "explanations": {
            "client": "同じコンセントでスマホが充電できるなら、原因はデスクライト(個別設備)の故障だね。",
            "local": "別の部屋の電気はつくので、原因はその部屋のコンセント周り(配線)だね。",
            "gateway": "家中の電気がつかずブレーカーが落ちている。原因は自宅と外部の境界(ブレーカー)だね。",
            "external": "ブレーカーは正常なのに電気が来ない。原因は外部(電力会社側)の停電だね。",
        },
        "choices": {"client": "💡 デスクライト本体", "local": "🔌 部屋のコンセント", "gateway": "⚡ 家のブレーカー", "external": "🏢 電力会社"},
    },
    "water": {
        "title": "キッチンの水が出ない！(水道)",
        "order": ["client", "local", "gateway", "external"],
        "info": {
            "client": {"emoji": "🚰", "label": "キッチンの蛇口"},
            "local": {"emoji": "🚿", "label": "お風呂など他の蛇口"},
            "gateway": {"emoji": "🎛️", "label": "水道の元栓"},
            "external": {"emoji": "💧", "label": "水道局"},
        },
        "tests": {
            "test1": {"name": "🚿 お風呂や洗面所の水を出してみる", "desc": "キッチンだけの問題か、家全体の問題か切り分けるよ。"},
            "test2": {"name": "🔧 キッチンの下の止水栓を見る", "desc": "キッチン特有の設備に問題がないか確認するよ。"},
            "test3": {"name": "🎛️ 外にある水道メーター(元栓)を見る", "desc": "自宅と外部の『境界』に問題がないか確認するよ。"},
            "test4": {"name": "💧 水道局の断水情報を確認", "desc": "地域全体の問題ではないか確認するよ。"},
        },
        "results": {
            "client": {"test1": ("success", "🟢 お風呂の水は出た！"), "test2": ("fail", "🔴 キッチンの下の止水栓が閉まっていた！"), "test3": ("success", "🟢 外の元栓は開いている。"), "test4": ("success", "🟢 断水情報なし。")},
            "local": {"test1": ("success", "🟢 お風呂の水は出た！"), "test2": ("success", "🟢 キッチンの止水栓は開いている。"), "test3": ("success", "🟢 外の元栓は開いている。"), "test4": ("success", "🟢 断水情報なし。")},
            "gateway": {"test1": ("fail", "🔴 家中すべての水が出ない。"), "test2": ("success", "🟢 キッチンの止水栓は開いている。"), "test3": ("fail", "🔴 外のメーター横の元栓が閉まっている！"), "test4": ("success", "🟢 断水情報なし。")},
            "external": {"test1": ("fail", "🔴 家中すべての水が出ない。"), "test2": ("success", "🟢 キッチンの止水栓は開いている。"), "test3": ("success", "🟢 外の元栓は開いている。"), "test4": ("fail", "🔴 地域の水道管工事による断水のお知らせ！")},
        },
        "explanations": {
            "client": "他の場所の水は出る。原因はキッチンの蛇口か止水栓(個別設備)だね。",
            "local": "止水栓も開いているのにキッチンだけ出ない。原因はキッチンの配管(局所的な問題)だね。",
            "gateway": "家中の水が出ず、外の元栓が閉まっていた。原因は家と外部の境界(元栓)だね。",
            "external": "家の設備はすべて正常。原因は外部(水道局側)の断水だね。",
        },
        "choices": {"client": "🚰 キッチンの蛇口・止水栓", "local": "🚿 家の中の配管", "gateway": "🎛️ 水道の元栓", "external": "💧 水道局(断水)"},
    },
    "tv": {
        "title": "テレビの放送が映らない！(テレビ)",
        "order": ["client", "local", "gateway", "external"],
        "info": {
            "client": {"emoji": "📺", "label": "テレビ本体"},
            "local": {"emoji": "🔌", "label": "壁のアンテナ線"},
            "gateway": {"emoji": "📡", "label": "屋根のアンテナ"},
            "external": {"emoji": "🗼", "label": "放送局"},
        },
        "tests": {
            "test1": {"name": "🎮 テレビのメニュー画面や録画番組を見る", "desc": "放送波の問題か、テレビ画面自体の故障か切り分けるよ。"},
            "test2": {"name": "🔌 壁のアンテナ線が抜けていないか見る", "desc": "テレビまでの通信経路が繋がっているか確認するよ。"},
            "test3": {"name": "📡 外に出て屋根のアンテナを見る", "desc": "自宅と外部の『境界』である受信設備を確認するよ。"},
            "test4": {"name": "📱 スマホで放送局の障害情報を確認", "desc": "地域全体の問題ではないか確認するよ。"},
        },
        "results": {
            "client": {"test1": ("fail", "🔴 メニュー画面すら映らない。真っ暗！"), "test2": ("success", "🟢 アンテナ線は挿さっている。"), "test3": ("success", "🟢 屋根のアンテナは正常。"), "test4": ("success", "🟢 障害情報なし。")},
            "local": {"test1": ("success", "🟢 メニュー画面や録画は綺麗に映る！"), "test2": ("fail", "🔴 壁のアンテナ線が抜けていた！"), "test3": ("success", "🟢 屋根のアンテナは正常。"), "test4": ("success", "🟢 障害情報なし。")},
            "gateway": {"test1": ("success", "🟢 メニュー画面や録画は綺麗に映る！"), "test2": ("success", "🟢 アンテナ線はしっかり挿さっている。"), "test3": ("fail", "🔴 台風で屋根のアンテナが倒れている！"), "test4": ("success", "🟢 障害情報なし。")},
            "external": {"test1": ("success", "🟢 メニュー画面や録画は綺麗に映る！"), "test2": ("success", "🟢 アンテナ線は挿さっている。"), "test3": ("success", "🟢 屋根のアンテナは正常。"), "test4": ("fail", "🔴 放送塔のトラブルによる停波のお知らせ！")},
        },
        "explanations": {
            "client": "メニュー画面すら映らない。原因はテレビ本体(個別設備)の故障だね。",
            "local": "録画は映るのに放送が映らず、線が抜けていた。原因はテレビまでの配線(家庭内)だね。",
            "gateway": "配線は正常なのに受信できない。原因は家と外部の境界(屋根のアンテナ)だね。",
            "external": "自宅側の受信設備はすべて正常。原因は外部(放送局側)のトラブルだね。",
        },
        "choices": {"client": "📺 テレビ本体", "local": "🔌 壁のアンテナ線", "gateway": "📡 屋根のアンテナ", "external": "🗼 放送塔(放送局)"},
    }
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
    if "reveal_fault1" not in st.session_state:
        st.session_state.reveal_fault1 = False

    if "stage2_scenario" not in st.session_state:
        st.session_state.stage2_scenario = random.choice(list(SCENARIOS.keys()))
    if "fault2" not in st.session_state:
        scenario = SCENARIOS[st.session_state.stage2_scenario]
        st.session_state.fault2 = random.choice(scenario["order"])
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
    st.session_state.reveal_fault1 = False
    if full:
        st.session_state.stage1_cleared = False

def reset_stage2():
    st.session_state.stage2_scenario = random.choice(list(SCENARIOS.keys()))
    scenario = SCENARIOS[st.session_state.stage2_scenario]
    st.session_state.fault2 = random.choice(scenario["order"])
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
    status = {node: "unknown" for node in NET_ORDER}
    status["phone"] = "ok"
    for entry in st.session_state.history1:
        for node, ok in entry["results"]:
            status[node] = "ok" if ok else "fail"
    return status

def trigger_hint():
    st.session_state.reveal_fault1 = True

def render_network_diagram():
    st.markdown("#### 🗺️ 現在の通信経路")
    st.caption("アイコンの間の矢印「⇄」を押すと、どこでトラブルが起きているかヒント（赤点滅）が出るよ！")
    known = compute_known_status()
    icon_map = {"ok": "🟢", "fail": "🔴", "unknown": "⚪"}
    
    # 9つのカラムを作成（ノード5つ ＋ 矢印4つ）
    cols = st.columns([2, 1, 2, 1, 2, 1, 2, 1, 2])
    
    for i, node in enumerate(NET_ORDER):
        info = NET_INFO[node]
        col_idx = i * 2
        with cols[col_idx]:
            # 点滅フラグが立っていて、かつこのノードが障害箇所の場合
            if st.session_state.reveal_fault1 and node == st.session_state.fault1:
                st.markdown(f"<div class='flashing'><b>{info['emoji']}</b><br><small>{info['label']}</small></div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='normal-node'><b>{info['emoji']}</b><br><small>{info['label']}</small></div>", unsafe_allow_html=True)
            
            if node != "phone":
                st.markdown(f"<div style='text-align:center;'>{icon_map[known[node]]}</div>", unsafe_allow_html=True)
        
        # 矢印ボタンの配置
        if i < len(NET_ORDER) - 1:
            with cols[col_idx + 1]:
                st.write("") # 位置調整
                st.button("⇄", key=f"hint_btn_{i}", on_click=trigger_hint, help="ヒントを見る")

    st.caption("⚪ 未調査 🟢 応答あり(正常) 🔴 応答なし(異常)")

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

    st.session_state.history1.append({"name": test["name"], "results": results, "success": success})

def submit_answer1():
    st.session_state.attempts1 += 1
    st.session_state.quiz1_answered = True
    st.session_state.quiz1_correct = (st.session_state.answer1_radio == st.session_state.fault1)
    if st.session_state.quiz1_correct:
        st.session_state.stage1_cleared = True

def render_history1():
    if not st.session_state.history1:
        st.info("まだ調査していないよ。上のボタンから調査ツールを実行してみよう！")
        return
    st.markdown("#### 📋 これまでの調査ログ")
    for idx, entry in enumerate(reversed(st.session_state.history1), start=1):
        icon = "🟢 成功" if entry["success"] else "🔴 失敗"
        path_str = " → ".join(f"{NET_INFO[n]['emoji']}{'🟢' if ok else '🔴'}" for n, ok in entry["results"])
        st.write(f"{len(st.session_state.history1) - idx + 1}. **{entry['name']}** ： {icon} ｜ {path_str}")


# ============================================================
# ステージ2 用の補助関数
# ============================================================
def submit_answer2():
    st.session_state.attempts2 += 1
    st.session_state.quiz2_answered = True
    st.session_state.quiz2_correct = (st.session_state.answer2_radio == st.session_state.fault2)
    if st.session_state.quiz2_correct:
        st.session_state.stage2_cleared = True

def run_home_check(check_key, scenario):
    fault = st.session_state.fault2
    status, text = scenario["results"][fault][check_key]
    st.session_state.checked2[check_key] = (status, text)
    if status == "success":
        st.success(text)
    else:
        st.error(text)

def render_home_diagram(scenario):
    st.markdown("#### 🏠 仕組み(かんたん図)")
    cols = st.columns(len(scenario["order"]))
    for i, node in enumerate(scenario["order"]):
        info = scenario["info"][node]
        with cols[i]:
            st.markdown(f"**{info['emoji']}**")
            st.caption(info["label"])
    
    emoji_path = " → ".join([scenario["info"][n]["emoji"] for n in scenario["order"]])
    st.caption(f"{emoji_path} の順につながっているよ")

def render_checked_log(scenario):
    if not st.session_state.checked2:
        st.info("まだ何も確認していないよ。上のボタンから確認してみよう！")
        return
    st.markdown("#### 📋 これまでの確認ログ")
    for key, (status, text) in st.session_state.checked2.items():
        name = scenario["tests"][key]["name"]
        st.write(f"・**{name}**\n → {text}")


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
    if st.button("🔄 最初から全部やり直す", use_container_width=True, key="reset_all_btn"):
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
    if st.button(NET_TESTS["ping_router"]["name"], use_container_width=True, key="tool_ping_router"):
        with st.container(border=True):
            st.caption(NET_TESTS["ping_router"]["desc"])
            run_network_test("ping_router")
with col2:
    if st.button(NET_TESTS["ping_ip"]["name"], use_container_width=True, key="tool_ping_ip"):
        with st.container(border=True):
            st.caption(NET_TESTS["ping_ip"]["desc"])
            run_network_test("ping_ip")
with col3:
    if st.button(NET_TESTS["ping_url"]["name"], use_container_width=True, key="tool_ping_url"):
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

st.button("✅ この場所が原因だと思う！回答する", type="primary", key="submit1", on_click=submit_answer1)

if st.session_state.quiz1_answered:
    if st.session_state.quiz1_correct:
        st.success("🎉 正解！お見事、名探偵だね！")
        st.info(NET_EXPLANATIONS[st.session_state.fault1])
        st.balloons()
    else:
        st.error("😵 残念、不正解…もう一度調査結果を見直してみよう。")
        st.warning("ヒント：どのツールが🔴失敗して、どのツールが🟢成功したかを比べてみよう。『どこまでは届いたか』が一番大事な手がかりだよ。")

if st.session_state.stage1_cleared:
    st.success("🏆 ステージ1クリア！下のボタンで新しいパターンにも挑戦できるよ。")
    if st.button("🔁 別の障害パターンでもう一度挑戦する", key="retry1"):
        reset_stage1(full=False)
        st.rerun()

st.divider()

# ---------------- ステージ2 ----------------
if not st.session_state.stage1_cleared:
    st.header("🔒 ステージ2：日常トラブル応用編")
    st.info("ステージ1をクリアすると解放されるよ。まずはネットワークの障害を突き止めよう！")
else:
    scenario = SCENARIOS[st.session_state.stage2_scenario]
    
    st.header(f"🛁 ステージ2：{scenario['title']}")
    st.write("ネットワークで学んだ『切り分け』の考え方は、日常生活のトラブルにもそのまま使えるよ。さっそく試してみよう！")
    
    render_home_diagram(scenario)
    st.write("")

    hcol1, hcol2 = st.columns(2)
    hcol3, hcol4 = st.columns(2)
    home_cols = {"test1": hcol1, "test2": hcol2, "test3": hcol3, "test4": hcol4}
    
    for key, col in home_cols.items():
        with col:
            if st.button(scenario["tests"][key]["name"], use_container_width=True, key=f"btn_{key}"):
                with st.container(border=True):
                    st.caption(scenario["tests"][key]["desc"])
                    run_home_check(key, scenario)

    st.write("")
    render_checked_log(scenario)

    st.write("")
    st.subheader("🤔 推理タイム：トラブルの原因はどこ？")
    answer2 = st.radio(
        "確認結果から、原因を1つ選んでね",
        options=list(scenario["choices"].keys()),
        format_func=lambda k: scenario["choices"][k],
        key="answer2_radio",
    )

    st.button("✅ この場所が原因だと思う！回答する", type="primary", key="submit2", on_click=submit_answer2)

    if st.session_state.quiz2_answered:
        if st.session_state.quiz2_correct:
            st.success("🎉 正解！日常のトラブルでも見事に切り分けられたね！")
            st.info(scenario["explanations"][st.session_state.fault2])
            st.balloons()
        else:
            st.error("😵 残念、不正解…確認結果をもう一度比べてみよう。")
            st.warning("ヒント：『家全体の問題か、個別の設備だけの問題か』をまず切り分けるのがコツだよ。")

    if st.session_state.stage2_cleared:
        st.success("🏆 ステージ2クリア！おめでとう！")
        st.markdown(
            "### 🎓 学んだこと\n"
            "ネットワークのトラブルも、日常のトラブルも、考え方は同じだったね。\n\n"
            "- 経路を **区切って(分割して)**、一つずつ検証する\n"
            "- 『どこまでは正常で、どこから異常か』を手がかりに絞り込む\n"
            "- これが情報の世界でもくらしの中でも使える「切り分け」というエンジニアリングの考え方なんだ！"
        )
        if st.button("🔁 別のパターンの日常トラブルに挑戦する", key="retry2"):
            reset_stage2()
            st.rerun()