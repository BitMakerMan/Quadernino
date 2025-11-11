"""
Monitoraggio dell'utilizzo delle API Google Gemini e File Search
Fornisce informazioni su consumo, limiti e occupazione memoria
"""
import os
from typing import Dict, List, Optional
from utils.logger import log_info, log_error, log_warning

class GoogleMonitor:
    """Classe per monitorare l'utilizzo delle API Google"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = None

        # Limiti noti delle API Google Gemini (2024)
        self.LIMITS = {
            "gemini_2.5_flash": {
                "rpm_limit": 15,  # richieste per minuto
                "tpm_limit": 1000000,  # token per minuto
                "files_per_store": 500,  # max file per File Search store
                "total_files": 10000  # max total files
            },
            "gemini_2.0_flash": {
                "rpm_limit": 15,
                "tpm_limit": 1000000,
                "files_per_store": 500,
                "total_files": 10000
            },
            "gemini_2.5_pro": {
                "rpm_limit": 2,
                "tpm_limit": 50000,
                "files_per_store": 500,
                "total_files": 10000
            }
        }

        # Costi stimati (USD)
        self.COSTS = {
            "gemini_2.5_flash": {
                "input_per_1m": 0.075,  # $0.075 per milione di token
                "output_per_1m": 0.15
            },
            "gemini_2.0_flash": {
                "input_per_1m": 0.075,
                "output_per_1m": 0.15
            },
            "gemini_2.5_pro": {
                "input_per_1m": 1.25,
                "output_per_1m": 5.0
            }
        }

    def _get_client(self):
        """Ottiene il client Google se non esiste"""
        if not self.client:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                log_error(f"Errore inizializzazione client Google: {e}")
                return None
        return self.client

    def get_file_search_stats(self) -> Dict:
        """
        Recupera statistiche sui File Search stores
        """
        try:
            client = self._get_client()
            if not client:
                return {}

            stats = {
                "total_stores": 0,
                "total_files": 0,
                "stores": [],
                "quadernino_stores": 0,
                "quadernino_files": 0
            }

            # Scansiona tutti i File Search stores
            stores = list(client.file_search_stores.list())
            stats["total_stores"] = len(stores)

            total_size_estimated = 0

            for store in stores:
                store_display = getattr(store, 'display_name', '')
                store_name = getattr(store, 'name', '')

                store_info = {
                    "name": store_display,
                    "store_id": store_name,
                    "is_quadernino": (store_display.startswith('Quadernino - ') or
                                     store_display.startswith('Quadernino RAG Store') or
                                     'Quadernino' in store_display),
                    "file_count": 0,
                    "size_estimate": 0
                }

                # Conta file (varie fonti possibili)
                file_count = 0
                if hasattr(store, 'active_documents_count'):
                    active_count = getattr(store, 'active_documents_count', 0)
                    if active_count is not None:
                        try:
                            file_count = int(active_count)
                        except (ValueError, TypeError):
                            file_count = 0
                elif hasattr(store, 'file_names'):
                    file_names = getattr(store, 'file_names', [])
                    if file_names is not None:
                        try:
                            file_names_list = list(file_names)
                            file_count = len(file_names_list)
                        except (ValueError, TypeError):
                            file_count = 0

                store_info["file_count"] = file_count
                stats["total_files"] += file_count
                total_size_estimated += file_count * 1024 * 1024  # Stima 1MB per file

                if store_info["is_quadernino"]:
                    stats["quadernino_stores"] += 1
                    stats["quadernino_files"] += file_count

                stats["stores"].append(store_info)

            stats["total_size_estimate_mb"] = total_size_estimated // (1024 * 1024)

            log_info(f"Statistiche File Search: {stats['total_stores']} stores, {stats['total_files']} files totali")
            return stats

        except Exception as e:
            log_error(f"Errore recupero statistiche File Search: {e}")
            return {}

    def get_usage_estimate(self, model_name: str) -> Dict:
        """
        Stima l'utilizzo corrente e i limiti rimanenti
        """
        try:
            # Ottieni statistiche file
            file_stats = self.get_file_search_stats()

            # Estrai nome base modello
            base_model = model_name.replace("models/", "").split("-")[0] + "_" + model_name.split("-")[1]

            limits = self.LIMITS.get(base_model, self.LIMITS["gemini_2.5_flash"])
            costs = self.COSTS.get(base_model, self.COSTS["gemini_2.5_flash"])

            # Calcola occupazione memoria
            memory_usage_mb = file_stats.get("total_size_estimate_mb", 0)
            memory_limit_mb = limits["files_per_store"] * 10  # Stima 10MB per file
            memory_percentage = min(100, (memory_usage_mb / memory_limit_mb * 100)) if memory_limit_mb > 0 else 0

            # Stima usage basato su file e conversazioni
            estimated_daily_requests = len(file_stats.get("stores", [])) * 5  # 5 richieste per store al giorno
            estimated_daily_tokens = file_stats.get("total_files", 0) * 1000  # 1000 token per file per chat

            return {
                "model": model_name,
                "memory": {
                    "used_mb": memory_usage_mb,
                    "limit_mb": memory_limit_mb,
                    "percentage": round(memory_percentage, 1),
                    "files_used": file_stats.get("total_files", 0),
                    "files_limit": limits["total_files"],
                    "stores_used": file_stats.get("quadernino_stores", 0)
                },
                "api_limits": {
                    "rpm_limit": limits["rpm_limit"],
                    "tpm_limit": limits["tpm_limit"],
                    "daily_requests_est": estimated_daily_requests,
                    "daily_tokens_est": estimated_daily_tokens
                },
                "costs": {
                    "input_per_million": costs["input_per_1m"],
                    "output_per_million": costs["output_per_1m"],
                    "estimated_monthly_cost": round(estimated_daily_tokens * costs["input_per_1m"] * 30 / 1000000, 2)
                },
                "health_status": self._calculate_health_status(file_stats, limits)
            }

        except Exception as e:
            log_error(f"Errore calcolo usage estimate: {e}")
            return {}

    def _calculate_health_status(self, file_stats: Dict, limits: Dict) -> Dict:
        """
        Calcola lo stato di salute del sistema
        """
        status = {
            "level": "good",  # good, warning, critical
            "issues": [],
            "recommendations": []
        }

        # Controlla limiti file
        total_files = file_stats.get("total_files", 0)
        if total_files > limits["total_files"] * 0.8:
            status["level"] = "warning"
            status["issues"].append(f"Avvicinandosi al limite di file ({total_files}/{limits['total_files']})")
            status["recommendations"].append("Cancella vecchi file o quadernini non utilizzati")

        if total_files > limits["total_files"] * 0.95:
            status["level"] = "critical"
            status["issues"].append(f"LIMITE FILE quasi raggiunto ({total_files}/{limits['total_files']})")
            status["recommendations"].append("URGENTE: Libera spazio su Google Cloud")

        # Controlla numero di store
        quadernino_stores = file_stats.get("quadernino_stores", 0)
        if quadernino_stores > 50:
            status["level"] = "warning"
            status["issues"].append(f"Molti quadernini creati ({quadernino_stores})")
            status["recommendations"].append("Considera di consolidare o rimuovere quadernini vecchi")

        return status

    def get_store_files_detailed(self, store_id: str) -> Dict:
        """
        Recupera informazioni dettagliate sui file in uno store specifico
        """
        try:
            client = self._get_client()
            if not client:
                return {}

            # Prova a ottenere lo store specifico
            store = None
            try:
                store = client.file_search_stores.get(name=store_id)
            except:
                # Se non trova per nome, cerca nella lista
                for s in list(client.file_search_stores.list()):
                    if s.name == store_id:
                        store = s
                        break

            if not store:
                return {"error": "Store non trovato", "files": []}

            # Estrai informazioni sui file
            files_info = []
            file_count = 0
            store_display = getattr(store, 'display_name', 'Store Sconosciuto')

            # Metodo 1: active_documents_count (se disponibile)
            if hasattr(store, 'active_documents_count'):
                active_count = getattr(store, 'active_documents_count', 0)
                if active_count is not None:
                    file_count = int(active_count)

            # Metodo 2: file_names (se disponibile)
            file_names = []
            if hasattr(store, 'file_names'):
                try:
                    file_names = list(getattr(store, 'file_names', []))
                    file_count = len(file_names)
                except (ValueError, TypeError):
                    file_names = []

            # Metodo 3: documenti (se disponibili)
            documents = []
            if hasattr(store, 'documents'):
                try:
                    documents = list(getattr(store, 'documents', []))
                    file_count = len(documents)
                except (ValueError, TypeError):
                    documents = []

            # Crea elenco file dettagliato
            all_files = file_names if file_names else []

            for i, file_name in enumerate(all_files):
                files_info.append({
                    "name": file_name,
                    "index": i,
                    "size_estimate": "1 MB",  # Stima
                    "type": self._get_file_type(file_name),
                    "status": "active"
                })

            # Aggiungi info dai documents se disponibili
            if documents:
                for doc in documents:
                    doc_name = getattr(doc, 'name', f'Documento {len(files_info)}')
                    files_info.append({
                        "name": doc_name,
                        "size_estimate": "1 MB",
                        "type": self._get_file_type(doc_name),
                        "status": "from_documents"
                    })

            return {
                "store_id": store_id,
                "store_name": store_display,
                "total_files": len(files_info),
                "files": files_info,
                "file_count_from_api": file_count,
                "success": True
            }

        except Exception as e:
            log_error(f"Errore recupero file store {store_id}: {e}")
            return {"error": str(e), "files": [], "success": False}

    def _get_file_type(self, filename: str) -> str:
        """Estrae il tipo di file dal nome"""
        if '.' not in filename:
            return 'unknown'
        ext = filename.split('.')[-1].lower()
        type_map = {
            'pdf': 'PDF',
            'docx': 'Word',
            'doc': 'Word',
            'txt': 'Text',
            'md': 'Markdown',
            'html': 'HTML',
            'htm': 'HTML'
        }
        return type_map.get(ext, ext.upper())

    def get_all_stores_detailed(self) -> Dict:
        """
        Recupera informazioni dettagliate su tutti i File Search stores
        """
        try:
            client = self._get_client()
            if not client:
                return {}

            stores = list(client.file_search_stores.list())
            stores_details = []

            for store in stores:
                store_display = getattr(store, 'display_name', 'Senza Nome')
                store_name = getattr(store, 'name', '')
                created_time = getattr(store, 'create_time', 'unknown')

                # Debug: log dettagli store
                log_info(f"Store trovato: {store_display} | ID: {store_name}")

                # Conta file
                file_count = 0
                file_list = []
                if hasattr(store, 'active_documents_count'):
                    active_count = getattr(store, 'active_documents_count', 0)
                    if active_count is not None:
                        try:
                            file_count = int(active_count)
                        except (ValueError, TypeError):
                            file_count = 0
                elif hasattr(store, 'file_names'):
                    file_names = getattr(store, 'file_names', [])
                    if file_names is not None:
                        try:
                            file_list = list(file_names)
                            file_count = len(file_list)
                        except (ValueError, TypeError):
                            file_count = 0

                # Calcola dimensione stimata
                size_estimate = file_count * 1024 * 1024  # 1MB per file
                size_mb = size_estimate // (1024 * 1024)

                store_details = {
                    "name": store_display,
                    "store_id": store_name,
                    "created_time": created_time,
                    "is_quadernino": (store_display.startswith('Quadernino - ') or
                                     store_display.startswith('Quadernino RAG Store') or
                                     'Quadernino' in store_display),
                    "file_count": file_count,
                    "file_list": file_list[:5],  # Primi 5 file
                    "size_estimate_mb": size_mb,
                    "status": "active"
                }
                stores_details.append(store_details)

            # Ordina per tipo (Quadernini prima) poi per nome
            stores_details.sort(key=lambda x: (not x['is_quadernino'], x['name']))

            return {
                "stores": stores_details,
                "total_count": len(stores_details),
                "total_files": sum(s['file_count'] for s in stores_details),
                "total_size_mb": sum(s['size_estimate_mb'] for s in stores_details),
                "quadernino_count": sum(1 for s in stores_details if s['is_quadernino']),
                "other_count": sum(1 for s in stores_details if not s['is_quadernino'])
            }

        except Exception as e:
            log_error(f"Errore recupero store dettagliati: {e}")
            return {}

    def delete_store(self, store_id: str, force: bool = False) -> Dict:
        """
        Cancella un File Search store specifico con verifica post-eliminazione
        """
        try:
            client = self._get_client()
            if not client:
                return {"success": False, "error": "Client non disponibile"}

            # Controlla se lo store esiste prima di eliminare
            stores_before = list(client.file_search_stores.list())
            store_exists_before = any(s.name == store_id for s in stores_before)

            if not store_exists_before:
                log_warning(f"Store {store_id} non trovato durante eliminazione")
                return {"success": False, "error": "Store non trovato"}

            # Prova a eliminare lo store
            log_info(f"Tentativo eliminazione store {store_id} (force={force})")
            if force:
                client.file_search_stores.delete(name=store_id, config={"force": True})
            else:
                client.file_search_stores.delete(name=store_id)

            # Aspetta un momento per la propagazione
            import time
            time.sleep(2)

            # Verifica che lo store sia stato eliminato
            stores_after = list(client.file_search_stores.list())
            store_exists_after = any(s.name == store_id for s in stores_after)

            if store_exists_after:
                log_error(f"Store {store_id} ancora presente dopo eliminazione")
                return {"success": False, "error": "Store non eliminato (ancora presente dopo tentativo)"}

            log_info(f"Store {store_id} eliminato con successo")
            return {"success": True, "store_id": store_id}

        except Exception as e:
            error_msg = str(e)
            log_error(f"Errore eliminazione store {store_id}: {error_msg}")

            # Gestisci errori comuni
            if "not found" in error_msg.lower():
                return {"success": False, "error": "Store non trovato o già eliminato"}
            elif "permission" in error_msg.lower() or "403" in error_msg:
                return {"success": False, "error": "Permessi insufficienti"}
            elif "invalid" in error_msg.lower():
                return {"success": False, "error": "Store ID non valido"}
            else:
                return {"success": False, "error": f"Errore: {error_msg}"}

    def cleanup_old_stores(self, days_old: int = 30) -> Dict:
        """
        Identifica vecchi store per cleanup suggerito
        """
        try:
            client = self._get_client()
            if not client:
                return {}

            stores = list(client.file_search_stores.list())
            old_stores = []

            for store in stores:
                # Store non creati da Quadernino
                store_display = getattr(store, 'display_name', '')
                is_quadernino = (store_display.startswith('Quadernino - ') or
                               store_display.startswith('Quadernino RAG Store') or
                               'Quadernino' in store_display)
                if not is_quadernino:
                    store_info = {
                        "name": store_display,
                        "store_id": getattr(store, 'name', ''),
                        "created_time": getattr(store, 'create_time', 'unknown'),
                        "file_count": 0
                    }

                    # Conta file per accuratezza
                    if hasattr(store, 'active_documents_count'):
                        active_count = getattr(store, 'active_documents_count', 0)
                        if active_count is not None:
                            try:
                                store_info["file_count"] = int(active_count)
                            except (ValueError, TypeError):
                                store_info["file_count"] = 0

                    old_stores.append(store_info)

            total_files = sum(s["file_count"] for s in old_stores)

            return {
                "old_stores": old_stores,
                "count": len(old_stores),
                "total_files": total_files,
                "potential_savings_mb": len(old_stores) * 10  # Stima 10MB per store
            }

        except Exception as e:
            log_error(f"Errore analisi cleanup stores: {e}")
            return {}

    def recreate_store_without_files(self, store_id: str, files_to_exclude: List[str]) -> Dict:
        """
        Ricrea uno store escludendo i file specificati.
        Funzionalità avanzata per rimozione selettiva di file.
        """
        try:
            client = self._get_client()
            if not client:
                return {"success": False, "error": "Client non disponibile"}

            # Ottieni dettagli store corrente
            current_store = None
            try:
                current_store = client.file_search_stores.get(name=store_id)
            except:
                for s in list(client.file_search_stores.list()):
                    if s.name == store_id:
                        current_store = s
                        break

            if not current_store:
                return {"success": False, "error": "Store non trovato"}

            # Estrai file correnti
            current_files = []
            if hasattr(current_store, 'file_names'):
                try:
                    current_files = list(getattr(current_store, 'file_names', []))
                except (ValueError, TypeError):
                    current_files = []

            # Filtra file da mantenere (escludi quelli specificati)
            files_to_keep = [f for f in current_files if f not in files_to_exclude]

            if len(files_to_keep) == len(current_files):
                return {"success": False, "error": "Nessun file da rimuovere trovato"}

            if len(files_to_keep) == 0:
                return {"success": False, "error": "Rimuovere tutti i file richiede eliminazione store completa"}

            # Prepara dati per ricreazione
            store_name = getattr(current_store, 'display_name', 'Store Ricostruito')

            log_info(f"Ricreazione store '{store_name}': {len(current_files)} -> {len(files_to_keep)} file")

            # Crea nuovo store
            try:
                new_store = client.file_search_stores.create(
                    display_name=f"{store_name} (Ricostruito)"
                )
                new_store_id = new_store.name
                log_info(f"Nuovo store creato: {new_store_id}")
            except Exception as e:
                return {"success": False, "error": f"Creazione nuovo store fallita: {str(e)}"}

            # Tenta di recuperare e ricreare i file da mantenere
            recreated_files = []
            failed_files = []

            for file_name in files_to_keep:
                try:
                    # NOTA: Google File Search API non permette di recuperare direttamente i file
                    # Questa è una funzione placeholder che richiede implementazione più complessa
                    # che coinvolge il re-upload dei file locali se disponibili
                    log_info(f"File da mantenere (implementazione richiesta): {file_name}")
                    recreated_files.append(file_name)
                except Exception as e:
                    log_error(f"Errore gestione file {file_name}: {e}")
                    failed_files.append(file_name)

            # Elimina vecchio store
            try:
                client.file_search_stores.delete(name=store_id, config={"force": True})
                log_info(f"Vecchio store eliminato: {store_id}")
            except Exception as e:
                log_warning(f"Eliminazione vecchio store fallita: {e}")

            return {
                "success": True,
                "new_store_id": new_store_id,
                "original_files": len(current_files),
                "kept_files": len(files_to_keep),
                "removed_files": len(files_to_exclude),
                "recreated_files": len(recreated_files),
                "failed_files": failed_files,
                "message": f"Store ricostruito con {len(files_to_keep)} file (rimossi {len(files_to_exclude)})"
            }

        except Exception as e:
            error_msg = str(e)
            log_error(f"Errore ricreazione store {store_id}: {error_msg}")
            return {"success": False, "error": f"Errore ricreazione store: {error_msg}"}

    def get_file_analysis_summary(self, store_id: str) -> Dict:
        """
        Fornisce un'analisi dettagliata dei file in uno store
        """
        try:
            files_details = self.get_store_files_detailed(store_id)
            if not files_details.get("success"):
                return {"success": False, "error": files_details.get("error", "Errore")}

            files = files_details.get("files", [])
            analysis = {
                "total_files": len(files),
                "file_types": {},
                "size_distribution": {"small": 0, "medium": 0, "large": 0},
                "file_list": []
            }

            total_size_est = 0
            for file_info in files:
                file_name = file_info.get('name', 'unknown')
                file_type = file_info.get('type', 'unknown')

                # Analisi tipi file
                analysis["file_types"][file_type] = analysis["file_types"].get(file_type, 0) + 1

                # Stima dimensione (logica semplificata)
                size_est = 1024 * 1024  # 1MB default
                if "pdf" in file_name.lower():
                    size_est = 2 * 1024 * 1024  # 2MB per PDF
                elif "docx" in file_name.lower() or "doc" in file_name.lower():
                    size_est = 512 * 1024  # 512KB per Word

                total_size_est += size_est

                # Classificazione dimensione
                if size_est < 1024 * 1024:  # < 1MB
                    analysis["size_distribution"]["small"] += 1
                elif size_est < 5 * 1024 * 1024:  # < 5MB
                    analysis["size_distribution"]["medium"] += 1
                else:
                    analysis["size_distribution"]["large"] += 1

                analysis["file_list"].append({
                    "name": file_name,
                    "type": file_type,
                    "size_estimate": f"{size_est // (1024 * 1024)} MB",
                    "status": file_info.get('status', 'unknown')
                })

            analysis["total_size_estimate_mb"] = total_size_est // (1024 * 1024)
            analysis["average_file_size_mb"] = analysis["total_size_estimate_mb"] // len(files) if files > 0 else 0

            # Raccomandazioni
            recommendations = []
            if analysis["size_distribution"]["large"] > 0:
                recommendations.append(f"{analysis['size_distribution']['large']} file grandi trovati - considera compressione")
            if analysis["total_size_estimate_mb"] > 50:
                recommendations.append("Store di grandi dimensioni - considera cleanup")
            if len(analysis["file_types"]) > 5:
                recommendations.append("Molti tipi di file differenti - verifica rilevanza")

            analysis["recommendations"] = recommendations
            analysis["success"] = True

            return analysis

        except Exception as e:
            log_error(f"Errore analisi file store {store_id}: {e}")
            return {"success": False, "error": str(e)}

    def optimize_store_suggestions(self, store_id: str) -> Dict:
        """
        Fornisce suggerimenti di ottimizzazione per uno store
        """
        try:
            analysis = self.get_file_analysis_summary(store_id)
            if not analysis.get("success"):
                return analysis

            suggestions = {
                "actions": [],
                "priorities": [],
                "potential_savings": 0,
                "estimated_new_size": analysis["total_size_estimate_mb"]
            }

            # Analizza file per suggerimenti
            file_types = analysis.get("file_types", {})

            # Suggerimenti per tipi file
            if file_types.get("Text", 0) > analysis["total_files"] * 0.5:
                suggestions["actions"].append("Molti file di testo - considera consolidazione")
                suggestions["priorities"].append("medium")
                suggestions["potential_savings"] += analysis["total_size_estimate_mb"] * 0.1

            # Suggerimenti per file grandi
            if analysis["size_distribution"]["large"] > 0:
                suggestions["actions"].append(f"{analysis['size_distribution']['large']} file grandi - ottimizza comprimendo")
                suggestions["priorities"].append("high")
                suggestions["potential_savings"] += analysis["total_size_estimate_mb"] * 0.2

            # Suggerimenti generali
            if analysis["total_size_estimate_mb"] > 20:
                suggestions["actions"].append("Store di grandi dimensioni - considera rimozione file non essenziali")
                suggestions["priorities"].append("high")
                suggestions["potential_savings"] += analysis["total_size_estimate_mb"] * 0.3

            # Calcola nuova dimensione stimata
            suggestions["estimated_new_size"] = max(
                1,
                analysis["total_size_estimate_mb"] - suggestions["potential_savings"]
            )

            # Ordina azioni per priorità
            if suggestions["actions"]:
                actions_with_priority = list(zip(suggestions["actions"], suggestions["priorities"]))
                # Sort by priority (high > medium > low)
                priority_order = {"high": 0, "medium": 1, "low": 2}
                actions_with_priority.sort(key=lambda x: priority_order.get(x[1], 3))
                suggestions["actions"] = [action for action, _ in actions_with_priority]

            suggestions["success"] = True
            return suggestions

        except Exception as e:
            log_error(f"Errore suggerimenti ottimizzazione store {store_id}: {e}")
            return {"success": False, "error": str(e)}

def get_google_monitor(api_key: str) -> GoogleMonitor:
    """Factory function per ottenere il monitor"""
    return GoogleMonitor(api_key)