import re
import sys
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple

from src.config import config

# Optional Neo4j Driver Import
try:
    from neo4j import GraphDatabase, Driver
    HAS_NEO4J_SDK = True
except ImportError:
    HAS_NEO4J_SDK = False
    Driver = Any


class KnowledgeGraph:
    """
    Knowledge Graph Engine supporting Multi-Graph Domains (WORK, PERSONAL, DEVELOPMENT),
    Multi-App Conversational Contexts, Recipient Profiles, and Neo4j + Local Graph Fallback.
    """

    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"
        
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.graph_file = self.data_dir / "knowledge_graph.json"
        self._cached_recipient: Optional[str] = None  # set by main.py to avoid double vision API calls
        
        self.neo4j_driver: Optional[Driver] = None
        self._init_neo4j()
        self._init_local_graph()

    def _init_neo4j(self):
        """Initializes connection to native Neo4j Community Edition server if configured."""
        if HAS_NEO4J_SDK and config.NEO4J_ENABLED and config.NEO4J_PASSWORD:
            try:
                import socket, urllib.parse
                parsed = urllib.parse.urlparse(config.NEO4J_URI)
                host = parsed.hostname or "localhost"
                port = parsed.port or 7687
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.15)
                res = sock.connect_ex((host, port))
                sock.close()
                if res != 0:
                    self.neo4j_driver = None
                    return

                driver = GraphDatabase.driver(
                    config.NEO4J_URI,
                    auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
                )
                with driver.session() as session:
                    session.run("RETURN 1 AS test")
                self.neo4j_driver = driver
            except Exception:
                self.neo4j_driver = None

    def sync_local_to_neo4j(self) -> int:
        """Syncs all nodes and edges from local JSON store into Neo4j database."""
        if not self.neo4j_driver:
            return 0
        
        graph = self._read_local_graph()
        nodes = graph.get("nodes", {})
        edges = graph.get("edges", [])

        count = 0
        with self.neo4j_driver.session() as session:
            for name, meta in nodes.items():
                ntype = meta.get("type", "CONCEPT")
                freq = meta.get("frequency", 1)
                session.run(
                    """
                    MERGE (n:KnowledgeNode {name: $name})
                    SET n.type = $ntype, n.frequency = $freq, n.last_seen = datetime()
                    """,
                    name=name, ntype=ntype, freq=freq
                )
                count += 1
            
            for edge in edges:
                src = edge.get("source")
                tgt = edge.get("target")
                rel = edge.get("relation", "RELATED_TO").replace(" ", "_").replace("-", "_").upper()
                weight = edge.get("weight", 1)
                try:
                    session.run(
                        f"""
                        MATCH (s:KnowledgeNode {{name: $src}})
                        MATCH (t:KnowledgeNode {{name: $tgt}})
                        MERGE (s)-[r:{rel}]->(t)
                        SET r.weight = $weight
                        """,
                        src=src, tgt=tgt, weight=weight
                    )
                except Exception:
                    pass

        return count

    def _init_local_graph(self):
        if not self.graph_file.exists():
            default_graph = {
                "nodes": {
                    "System-Wide AI Copilot": {"type": "PROJECT", "frequency": 1, "last_seen": datetime.now().isoformat()},
                    "Antigravity IDE": {"type": "TOOL", "frequency": 1, "last_seen": datetime.now().isoformat()},
                    "Python": {"type": "TECH", "frequency": 1, "last_seen": datetime.now().isoformat()},
                    "AutoHotkey v2": {"type": "TECH", "frequency": 1, "last_seen": datetime.now().isoformat()},
                    "Groq API": {"type": "SERVICE", "frequency": 1, "last_seen": datetime.now().isoformat()},
                    "Neo4j": {"type": "DATABASE", "frequency": 1, "last_seen": datetime.now().isoformat()}
                },
                "edges": [
                    {"source": "System-Wide AI Copilot", "target": "Python", "relation": "BUILT_WITH", "weight": 1},
                    {"source": "System-Wide AI Copilot", "target": "AutoHotkey v2", "relation": "BUILT_WITH", "weight": 1},
                    {"source": "System-Wide AI Copilot", "target": "Neo4j", "relation": "USES_GRAPH_DB", "weight": 1}
                ],
                "last_updated": datetime.now().isoformat()
            }
            self._write_local_graph(default_graph)

    def _read_local_graph(self) -> Dict[str, Any]:
        if not self.graph_file.exists():
            return {"nodes": {}, "edges": [], "last_updated": datetime.now().isoformat()}
        try:
            with open(self.graph_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"nodes": {}, "edges": [], "last_updated": datetime.now().isoformat()}

    def _write_local_graph(self, graph: Dict[str, Any]):
        graph["last_updated"] = datetime.now().isoformat()
        with open(self.graph_file, "w", encoding="utf-8") as f:
            json.dump(graph, f, ensure_ascii=False, indent=2)

    def extract_recipient(self, title: str, process: str) -> Optional[str]:
        """Extracts active recipient/chat person from window title."""
        if not title or title == "Unknown":
            return None

        # Ignore words that are app/browser names, URLs, or domains, never a person
        _IGNORE = {
            "whatsapp", "whatsapp web", "whatsapp chat", "chrome", "edge",
            "google chrome", "microsoft edge", "whats", "web", "app", "chat",
            "teams", "microsoft teams", "slack", "discord", "outlook", "gmail",
            "calendar", "inbox", "localhost", "neo4j browser", "neo4j", "browser"
        }

        def _is_valid_name(s: str) -> bool:
            """Returns True if s looks like a real contact name (2+ chars, not an app/domain keyword)."""
            s = s.strip().lstrip("'").strip()  # strip leading apostrophe from Chrome truncation
            if not s or s.lower() in _IGNORE:
                return False
            # Reject URLs, domain names, localhost
            if re.search(r'\.(com|microsoft|org|net|io|edu|gov|cloud|app|dev|local)\b', s, flags=re.IGNORECASE):
                return False
            if s.lower().startswith("http") or "localhost" in s.lower():
                return False
            # Accept: starts with letter/digit, 2-40 chars, allows apostrophe/space/dot/dash
            return bool(re.match(r"^[A-Za-z\d][A-Za-z0-9\s.'()\-]{1,39}$", s))

        if "whatsapp" in title.lower():
            # Strip notification count prefix: "(5) Mom - WhatsApp" → "Mom - WhatsApp"
            clean = re.sub(r'^\(\d+\)\s*', '', title).strip()
            # Split on any dash/pipe/en-dash/em-dash variant
            parts = [p.strip() for p in re.split(r'\s*[-–—|]\s*', clean) if p.strip()]
            for part in parts:
                if _is_valid_name(part):
                    return part.strip().lstrip("'").strip()

        # 2. Slack / Teams / Email Formats e.g. "Slack | Mohil" or "RE: Project - Sandeep"
        split_parts = [p.strip() for p in re.split(r'[-|:–—]', title) if p.strip()]
        for part in split_parts:
            if _is_valid_name(part):
                return part.strip()

        return None

    def _clean_response_name(self, raw: str) -> Optional[str]:
        raw = raw.strip()
        bold_match = re.search(r'\*\*([^*]+)\*\*', raw)
        if bold_match:
            candidate = bold_match.group(1).strip(' "\'`.')
            if candidate and candidate.upper() != "UNKNOWN" and len(candidate) < 40:
                return candidate

        clean = re.sub(
            r'^(the (contact|recipient|person)(\'s)? (name )?(in the image )?is|contact name:|recipient:|\"|\')',
            '', raw, flags=re.IGNORECASE
        ).strip(' "\'`.')

        if " is " in clean.lower():
            clean = clean.split(" is ")[-1].strip(' "\'`.')

        if clean and clean.upper() != "UNKNOWN" and len(clean) < 40 and not clean.lower().startswith("the "):
            return clean
        return None

    def extract_recipient_from_screenshot(self, screenshot_path: str) -> Optional[str]:
        """Extracts contact/recipient name from silent background window header screenshot using Vision model."""
        # Return cached result if main.py already pre-extracted it (avoids double vision API call)
        if self._cached_recipient is not None:
            return self._cached_recipient
        if not screenshot_path or not Path(screenshot_path).exists():
            sys.stderr.write(f"[KG] extract_recipient_from_screenshot: file missing {screenshot_path}\n")
            return None
        try:
            from PIL import Image
            import tempfile

            compressed_path = screenshot_path
            is_jpeg = False
            try:
                img = Image.open(screenshot_path)
                img.thumbnail((1024, 1024))
                temp_jpg = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                compressed_path = temp_jpg.name
                temp_jpg.close()
                img.convert("RGB").save(compressed_path, format="JPEG", quality=75)
                is_jpeg = True
            except Exception as compress_err:
                sys.stderr.write(f"[KG] extract_recipient_from_screenshot: compress error: {compress_err}\n")

            from src.llm_client import LLMClient
            llm = LLMClient()
            system_prompt = (
                "You are a specialized OCR Vision & Contact Identifier. "
                "Analyze the application window screenshot (WhatsApp, Slack, Teams, Email, Discord, or Browser). "
                "Locate the active chat recipient, contact name, or group chat header bar.\n\n"
                "STRICT CONSTRAINTS:\n"
                "- Output ONLY the clean contact/person/group name (e.g., 'Mom', 'Mohil', 'Alex').\n"
                "- DO NOT output browser titles, application names, domain names, or keywords like 'WhatsApp', 'Chrome', 'Teams', 'Slack', 'Inbox', 'Google Chrome', 'New Tab'.\n"
                "- If no specific contact or person name is visible, output UNKNOWN."
            )
            user_prompt = (
                "Extract the active contact/recipient name from this application window capture. "
                "Return ONLY the plain contact name string or UNKNOWN."
            )
            # Pass is_jpeg flag so generate_rewrite uses correct MIME type
            res = llm.generate_rewrite(system_prompt, user_prompt, image_path=compressed_path, image_mime="image/jpeg" if is_jpeg else "image/png")
            sys.stderr.write(f"[KG] extract_recipient_from_screenshot: vision result success={res.get('success')} text={repr(res.get('rewritten_text',''))} error={res.get('error')}\n")

            if compressed_path != screenshot_path and os.path.exists(compressed_path):
                try:
                    os.remove(compressed_path)
                except Exception:
                    pass

            if res.get("success"):
                return self._clean_response_name(res.get("rewritten_text", ""))
        except Exception as ex:
            import traceback
            sys.stderr.write(f"[KG] extract_recipient_from_screenshot EXCEPTION: {traceback.format_exc()}\n")
        return None

    def extract_categorized_entities(self, text: str, context: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Uses LLM inference to extract high-value categorized entities from interaction text and context.
        Categories: Person, Technology, Organization, Project, Topic.
        Filters out generic filler words.
        """
        if not text or len(text.strip()) == 0:
            return {}

        title = context.get("title", "")
        process = context.get("process", "")

        try:
            from src.llm_client import LLMClient
            llm = LLMClient()
            system_prompt = (
                "You are an expert Knowledge Graph Information Extraction system.\n"
                "Extract specific, high-value named entities from the text and active window context.\n"
                "Categorize them strictly into: Person, Technology, Organization, Project, Topic.\n"
                "DO NOT extract generic English filler words, verbs, or common adjectives (e.g. 'Text', 'Refining', 'Greeting', 'Please', 'Using').\n"
                "CRITICAL OUTPUT CONSTRAINT: Output ONLY valid JSON matching this exact structure with no conversational explanation:\n"
                '{"Person": [], "Technology": [], "Organization": [], "Project": [], "Topic": []}'
            )
            user_prompt = (
                f"Active Process: {process}\n"
                f"Window Title: {title}\n"
                f"Input Text: '{text[:1000]}'\n\n"
                "Extract categorized entities as pure JSON."
            )
            res = llm.generate_rewrite(system_prompt, user_prompt)
            if res.get("success"):
                cleaned = re.sub(r'```json\s*|\s*```', '', res.get("rewritten_text", "")).strip()
                match = re.search(r'\{.*\}', cleaned, re.DOTALL)
                if match:
                    return json.loads(match.group(0))
        except Exception:
            pass

        return {}

    def extract_entities(self, text: str, context: Dict[str, Any]) -> List[str]:
        """Extracts key entities as flat list from categorized extraction."""
        cat = self.extract_categorized_entities(text, context)
        entities: Set[str] = set()
        for _, items in cat.items():
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, str) and len(item.strip()) > 1:
                        entities.add(item.strip())

        tech_keywords = [
            "Python", "JavaScript", "TypeScript", "AutoHotkey", "React", "Node",
            "Groq", "OpenAI", "Claude", "ChatGPT", "Antigravity", "Docker", "Git",
            "Neo4j", "Cypher", "REST API", "JSON", "VS Code", "Notion", "Slack", "WhatsApp"
        ]
        combined = f"{context.get('title', '')} {text}"
        for kw in tech_keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', combined, re.IGNORECASE):
                entities.add(kw)

        return list(entities)

    def extract_recipient_from_text(self, title: str, text: str, process: str) -> Optional[str]:
        """Extracts contact/recipient name from message text and context using LLM inference."""
        if not text or len(text.strip()) == 0:
            return None
        try:
            from src.llm_client import LLMClient
            llm = LLMClient()
            system_prompt = (
                "You are an NLP recipient extraction model. "
                "Identify the person, contact name, or chat recipient being addressed or communicated with.\n"
                "Output ONLY the plain contact name string (e.g. 'Mana', 'Mom', 'Mohil'). "
                "If no recipient or person name can be identified, output UNKNOWN."
            )
            user_prompt = (
                f"App Process: {process}\n"
                f"Window Title: {title}\n"
                f"Message Text: '{text}'\n\n"
                "Extract recipient name or UNKNOWN."
            )
            res = llm.generate_rewrite(system_prompt, user_prompt)
            if res.get("success"):
                return self._clean_response_name(res.get("rewritten_text", ""))
        except Exception:
            pass
        return None

    def _derive_service_and_context(self, title: str, process: str, screenshot_path: Optional[str] = None, text: str = "") -> Tuple[str, str]:
        """
        Derives Service (e.g. 'WhatsApp Web', 'AI Web Workspace', 'IDE Editor') and Context Node name
        from the window title, active process, optional screenshot, and selected text.
        """
        proc_lower = process.lower()
        title_lower = title.lower()

        # 1. WhatsApp Web
        if "whatsapp" in title_lower or "whatsapp" in proc_lower:
            recipient = self.extract_recipient(title, process)
            if not recipient and screenshot_path:
                recipient = self.extract_recipient_from_screenshot(screenshot_path)
            context_name = f"Chat: {recipient}" if recipient else "WhatsApp Chat"
            return ("WhatsApp Web", context_name)

        # 2. Microsoft Teams (Web & Desktop App)
        if "teams" in title_lower or "teams" in proc_lower:
            recipient = self.extract_recipient(title, process)
            if not recipient and screenshot_path:
                recipient = self.extract_recipient_from_screenshot(screenshot_path)
            context_name = f"Chat: {recipient}" if recipient else "Teams Chat"
            return ("Microsoft Teams", context_name)

        # 3. Slack (Web & Desktop App)
        if "slack" in title_lower or "slack" in proc_lower:
            recipient = self.extract_recipient(title, process)
            if not recipient and screenshot_path:
                recipient = self.extract_recipient_from_screenshot(screenshot_path)
            context_name = f"Chat: {recipient}" if recipient else "Slack Workspace"
            return ("Slack", context_name)

        # 4. Discord (Web & Desktop App)
        if "discord" in title_lower or "discord" in proc_lower:
            recipient = self.extract_recipient(title, process)
            if not recipient and screenshot_path:
                recipient = self.extract_recipient_from_screenshot(screenshot_path)
            context_name = f"Chat: {recipient}" if recipient else "Discord Channel"
            return ("Discord", context_name)

        # 5. ChatGPT / Claude / Gemini / AI Tools
        if "chatgpt" in title_lower or "claude" in title_lower or "gemini" in title_lower:
            clean_title = re.sub(r'\s*-\s*(Google Chrome|Microsoft Edge|ChatGPT|Claude|Gemini)$', '', title, flags=re.IGNORECASE).strip()
            return ("AI Web Workspace", clean_title if clean_title else "AI Prompt Chat")

        # 6. GitHub Web
        if "github" in title_lower:
            clean_title = re.split(r'[-|]', title)[0].strip()
            return ("GitHub Web", clean_title if clean_title else "GitHub Repository")

        # 7. Code Editors (IDE, VS Code, Notepad)
        if "code" in proc_lower or "ide" in proc_lower or "notepad" in proc_lower:
            clean_title = re.split(r'[-|]', title)[0].strip()
            return ("IDE Editor", clean_title if clean_title else "Source File")

        # 8. Default App Service
        recipient = self.extract_recipient(title, process)
        if not recipient and screenshot_path:
            recipient = self.extract_recipient_from_screenshot(screenshot_path)
        clean_title = f"Chat: {recipient}" if recipient else (re.split(r'[-|]', title)[0].strip() if title and title != "Unknown" else "General Activity")
        app_name = process.replace(".exe", "").capitalize()
        return (f"{app_name} Service", clean_title)

    def update_graph(
        self,
        entities: List[str],
        process_name: str,
        title: str,
        domain: str = "GENERAL",
        preferences: Optional[Dict[str, Any]] = None,
        original_text: str = "",
        rewritten_text: str = "",
        project_name: str = "Default Project",
        workspace_meta: Optional[Dict[str, Any]] = None,
        screenshot_path: Optional[str] = None
    ):
        """Updates hierarchical ProjectWorkspace -> Application -> Service -> ContextNode -> Interaction -> Entity nodes in Neo4j & local store."""
        import uuid
        service_name, context_name = self._derive_service_and_context(title, process_name, screenshot_path=screenshot_path, text=original_text)

        interaction_id = str(uuid.uuid4())[:8]

        category = workspace_meta.get("category", "General") if workspace_meta else "General"
        priority = workspace_meta.get("priority", "NORMAL") if workspace_meta else "NORMAL"

        # 1. Update Neo4j Native Graph if connected
        if self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    # Build Hierarchical Chain: ProjectWorkspace -> Application -> Service -> ContextNode
                    session.run(
                        """
                        MERGE (proj:ProjectWorkspace {name: $project})
                        MERGE (d:GraphDomain {name: $domain})
                        MERGE (a:Application {name: $proc})
                        MERGE (s:Service {name: $service})
                        MERGE (c:ContextNode {name: $context})

                        MERGE (proj)-[:HAS_APPLICATION]->(a)
                        MERGE (d)-[:INCLUDES_APP]->(a)
                        MERGE (a)-[:RUNS_SERVICE]->(s)
                        MERGE (s)-[:HAS_CONTEXT]->(c)

                        SET proj.category = $category, proj.priority = $priority, proj.last_seen = datetime(), a.last_seen = datetime(), s.last_seen = datetime(), c.last_seen = datetime()
                        """,
                        project=project_name, domain=domain, proc=process_name, service=service_name, context=context_name, category=category, priority=priority
                    )

                    # Create Interaction Node connected to ContextNode
                    if original_text or rewritten_text:
                        session.run(
                            """
                            MATCH (c:ContextNode {name: $context})
                            CREATE (i:Interaction {
                                id: $id,
                                original_text: $orig,
                                rewritten_text: $rew,
                                title: $title,
                                timestamp: datetime()
                            })
                            MERGE (c)-[:LOGGED_INTERACTION]->(i)
                            """,
                            context=context_name, id=interaction_id, orig=original_text, rew=rewritten_text, title=title
                        )

                    # Connect User Preferences to Service
                    if preferences:
                        lang_style = preferences.get("language_style", "")
                        formality = preferences.get("formality", "")
                        if lang_style:
                            session.run(
                                """
                                MATCH (s:Service {name: $service})
                                MERGE (p:UserPreference {name: $style})
                                SET p.category = 'LanguageStyle', p.last_seen = datetime()
                                MERGE (s)-[:LEARNED_PREFERENCE]->(p)
                                """,
                                service=service_name, style=lang_style
                            )
                        if formality:
                            session.run(
                                """
                                MATCH (s:Service {name: $service})
                                MERGE (p:UserPreference {name: $formality})
                                SET p.category = 'Formality', p.last_seen = datetime()
                                MERGE (s)-[:LEARNED_PREFERENCE]->(p)
                                """,
                                service=service_name, formality=formality
                            )

                    # Connect Entities / Concepts directly to the Interaction event
                    for ent in entities:
                        if original_text or rewritten_text:
                            session.run(
                                """
                                MERGE (e:Entity {name: $ent})
                                SET e.last_seen = datetime()
                                WITH e
                                MATCH (i:Interaction {id: $id})
                                MERGE (i)-[:EXTRACTED_CONCEPT]->(e)
                                """,
                                id=interaction_id, ent=ent
                            )
                        else:
                            session.run(
                                """
                                MERGE (e:Entity {name: $ent})
                                SET e.last_seen = datetime()
                                WITH e
                                MATCH (c:ContextNode {name: $context})
                                MERGE (c)-[:USES_CONCEPT]->(e)
                                """,
                                context=context_name, ent=ent
                            )
            except Exception:
                pass

        # 2. Update Local Graph Store
        graph = self._read_local_graph()
        nodes = graph.get("nodes", {})
        edges = graph.get("edges", [])
        now_str = datetime.now().isoformat()

        domain_key = f"Domain:{domain}"
        if domain_key not in nodes:
            nodes[domain_key] = {"type": "DOMAIN", "frequency": 1, "last_seen": now_str}

        app_node_key = process_name
        if app_node_key not in nodes:
            nodes[app_node_key] = {"type": "APPLICATION", "frequency": 1, "last_seen": now_str}
        else:
            nodes[app_node_key]["frequency"] += 1
            nodes[app_node_key]["last_seen"] = now_str

        service_key = f"Service:{service_name}"
        if service_key not in nodes:
            nodes[service_key] = {"type": "SERVICE", "frequency": 1, "last_seen": now_str}

        context_key = f"Context:{context_name}"
        if context_key not in nodes:
            nodes[context_key] = {"type": "CONTEXT", "frequency": 1, "last_seen": now_str}

        self._add_or_increment_edge(edges, domain_key, app_node_key, "INCLUDES_APP")
        self._add_or_increment_edge(edges, app_node_key, service_key, "RUNS_SERVICE")
        self._add_or_increment_edge(edges, service_key, context_key, "HAS_CONTEXT")

        if original_text or rewritten_text:
            interaction_key = f"Interaction:{interaction_id}"
            nodes[interaction_key] = {
                "type": "INTERACTION",
                "original_text": original_text,
                "rewritten_text": rewritten_text,
                "title": title,
                "last_seen": now_str
            }
            self._add_or_increment_edge(edges, context_key, interaction_key, "LOGGED_INTERACTION")
            for ent in entities:
                if ent not in nodes:
                    nodes[ent] = {"type": "CONCEPT", "frequency": 1, "last_seen": now_str}
                self._add_or_increment_edge(edges, interaction_key, ent, "EXTRACTED_CONCEPT")

        if preferences:
            lang_style = preferences.get("language_style", "")
            if lang_style:
                pref_key = f"Preference:{lang_style}"
                if pref_key not in nodes:
                    nodes[pref_key] = {"type": "USER_PREFERENCE", "frequency": 1, "last_seen": now_str}
                self._add_or_increment_edge(edges, app_node_key, pref_key, "LEARNED_PREFERENCE")

        for ent in entities:
            if ent not in nodes:
                nodes[ent] = {"type": "CONCEPT", "frequency": 1, "last_seen": now_str}
            else:
                nodes[ent]["frequency"] += 1
                nodes[ent]["last_seen"] = now_str

            self._add_or_increment_edge(edges, app_node_key, ent, "USED_IN")

        graph["nodes"] = nodes
        graph["edges"] = edges
        self._write_local_graph(graph)

    def _add_or_increment_edge(self, edges: List[Dict[str, Any]], source: str, target: str, relation: str):
        for edge in edges:
            if edge.get("source") == source and edge.get("target") == target:
                edge["weight"] = edge.get("weight", 1) + 1
                return
        edges.append({
            "source": source,
            "target": target,
            "relation": relation,
            "weight": 1
        })

    def query_context(self, process_name: str, title: str, text: str, domain: str = "GENERAL", max_items: int = 8, screenshot_path: Optional[str] = None) -> List[str]:
        """Queries relevant knowledge graph memory snippets (timestamped interactions, preferences, context nodes, and entities) for prompt injection."""
        matched_memories: List[str] = []
        recipient = self.extract_recipient(title, process_name)
        if not recipient and screenshot_path:
            recipient = self.extract_recipient_from_screenshot(screenshot_path)

        if recipient:
            matched_memories.append(f"Active Recipient Context: '{recipient}' (Interacting via {process_name} under {domain} domain)")

        # 1. Query Neo4j Graph Database if active
        if self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    # Query recent logged interactions with timestamps
                    res_interactions = session.run(
                        """
                        MATCH (a:Application {name: $proc})-[:RUNS_SERVICE]->(s:Service)-[:HAS_CONTEXT]->(c:ContextNode)-[:LOGGED_INTERACTION]->(i:Interaction)
                        RETURN i.original_text AS orig, i.rewritten_text AS rew, i.title AS title, i.timestamp AS ts
                        ORDER BY i.timestamp DESC LIMIT 3
                        """,
                        proc=process_name
                    )
                    for record in res_interactions:
                        orig = (record.get("orig") or "")[:70].replace("\n", " ")
                        rew = (record.get("rew") or "")[:70].replace("\n", " ")
                        ts = str(record.get("ts") or "Recent")[:19]
                        matched_memories.append(f"Neo4j Knowledge Interaction [{ts}]: User: '{orig}' -> AI: '{rew}'")

                    # Query learned domain entities
                    res_entities = session.run(
                        """
                        MATCH (a:Application {name: $proc})-[r:USES_CONCEPT]->(e:Entity)
                        RETURN e.name AS entity, r.weight AS weight
                        ORDER BY r.weight DESC LIMIT $limit
                        """,
                        proc=process_name, limit=max_items
                    )
                    for record in res_entities:
                        matched_memories.append(f"Neo4j Domain Concept: '{record['entity']}' (Used in {domain}/{process_name}, weight: {record['weight']})")
            except Exception:
                pass

        # 2. Query Local Knowledge Graph Store
        graph = self._read_local_graph()
        nodes = graph.get("nodes", {})

        # A. Retrieve recent timestamped INTERACTION nodes for past conversation history & time-awareness
        interactions = []
        for node_name, meta in nodes.items():
            if meta.get("type") == "INTERACTION":
                interactions.append((node_name, meta))
        
        interactions.sort(key=lambda x: x[1].get("last_seen", ""), reverse=True)
        for node_name, meta in interactions[:3]:
            orig = (meta.get("original_text") or "")[:75].replace("\n", " ")
            rew = (meta.get("rewritten_text") or "")[:75].replace("\n", " ")
            last_seen = meta.get("last_seen", "")[:19].replace("T", " ")
            entry = f"Graph Memory Interaction [{last_seen}]: Input: '{orig}' -> Rewritten: '{rew}'"
            if entry not in matched_memories:
                matched_memories.append(entry)

        # B. Retrieve Learned User Preferences & Spoken User Facts
        for node_name, meta in nodes.items():
            ntype = meta.get("type")
            if ntype == "USER_PREFERENCE" or node_name.startswith("Preference:"):
                pref_name = node_name.replace("Preference:", "")
                entry = f"Learned User Style Preference: '{pref_name}'"
                if entry not in matched_memories:
                    matched_memories.append(entry)
            elif ntype == "USER_FACT" or node_name.startswith("UserFact:"):
                fact_val = meta.get("fact", node_name.replace("UserFact:", ""))
                entry = f"Remembered User Fact: '{fact_val}'"
                if entry not in matched_memories:
                    matched_memories.append(entry)

        # C. Retrieve Context & Concept Entities matching input keywords or context title
        combined_query = f"{domain} {process_name} {title} {text}".lower()
        query_words = set(re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', combined_query))

        for node_name, meta in nodes.items():
            if len(matched_memories) >= max_items + 5:
                break
            ntype = meta.get("type", "CONCEPT")
            if ntype in ("CONCEPT", "CONTEXT"):
                clean_name = node_name.replace("Context:", "")
                node_lower = clean_name.lower()
                if any(w in node_lower for w in query_words) or node_lower in combined_query:
                    freq = meta.get("frequency", 1)
                    entry_str = f"Knowledge Node: '{clean_name}' [{ntype}] (Used {freq}x in {domain})"
                    if entry_str not in matched_memories:
                        matched_memories.append(entry_str)

        return matched_memories

    def save_user_fact(self, fact_text: str) -> Dict[str, Any]:
        """Saves a spoken or typed long-term user fact/memory into the Knowledge Graph."""
        fact_clean = fact_text.strip()
        if not fact_clean:
            return {"success": False, "message": "Fact text cannot be empty."}

        # Remove common preamble prefixes like 'remember that', 'remember', 'save fact'
        fact_clean = re.sub(r'^(remember\s+that\s+|remember\s+|save\s+fact\s+|note\s+that\s+)', '', fact_clean, flags=re.IGNORECASE).strip()

        node_id = f"UserFact:{fact_clean[:60]}"
        now_str = datetime.now().isoformat()

        graph = self._read_local_graph()
        nodes = graph.get("nodes", {})
        nodes[node_id] = {
            "type": "USER_FACT",
            "fact": fact_clean,
            "frequency": nodes.get(node_id, {}).get("frequency", 0) + 1,
            "last_seen": now_str
        }
        graph["nodes"] = nodes
        self._write_local_graph(graph)

        if self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    session.run(
                        """
                        MERGE (n:UserFact {name: $node_id})
                        SET n.type = 'USER_FACT', n.fact = $fact, n.last_seen = datetime()
                        """,
                        node_id=node_id, fact=fact_clean
                    )
            except Exception:
                pass

        from src.tts_engine import announce_memory_saved
        announce_memory_saved(fact_clean)

        return {
            "success": True,
            "fact": fact_clean,
            "message": f"Saved fact memory: '{fact_clean}'"
        }

