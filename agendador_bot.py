import datetime
import time
import subprocess
import os
import sys

# Caminho absoluto para o Bot.py (A TI deve ajustar caso mude de pasta no servidor Linux)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_PATH = os.path.join(BASE_DIR, "Bot.py")

# Horários em que o bot DEVE rodar
HORARIOS_ALVO = ["08:30", "12:30", "17:25"]

# Registra qual foi o último dia (YYYY-MM-DD) que o bot rodou com SUCESSO para cada horário
ultimo_sucesso = {h: None for h in HORARIOS_ALVO}

def run_schedule():
    print("🚀 [Serviço de Agendamento do Bot Iniciado] Rodando 24/7 de forma independente...")
    
    while True:
        agora = datetime.datetime.now()
        dia_atual = agora.strftime("%Y-%m-%d")
        hora_atual = agora.strftime("%H:%M")
        houve_erro = False

        for h in HORARIOS_ALVO:
            # Condição de disparo: se já passou da hora alvo E ainda não registrou sucesso hoje
            if hora_atual >= h and ultimo_sucesso[h] != dia_atual:
                try:
                    print(f"[{agora.strftime('%H:%M:%S')}] Iniciando extração (Ciclo das {h})...")
                    
                    # Chama o Bot.py como um processo separado de forma segura
                    resultado = subprocess.run(
                        [sys.executable, BOT_PATH], 
                        capture_output=True, 
                        text=True, 
                        check=True
                    )
                    
                    # Se concluir sem disparar exceção (código 0), marcamos o sucesso!
                    ultimo_sucesso[h] = dia_atual
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ✅ Sucesso! Ciclo das {h} concluído.")
                
                except subprocess.CalledProcessError as e:
                    houve_erro = True
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ❌ Erro no ciclo das {h}.")
                    print(f"Detalhes do erro do Bot:\n{e.stderr}")
                    break # Sai do 'for' para não tentar rodar o próximo horário alvo imediatamente
                except Exception as e:
                    houve_erro = True
                    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ❌ Erro inesperado ao tentar chamar o Bot: {e}")
                    break

        # Se deu erro, dorme 10 minutos (600 segundos) e tenta de novo. 
        # Se está tudo normal, checa a cada 1 minuto (60 segundos).
        if houve_erro:
            print("⏳ Aguardando 10 minutos para tentar novamente devido a falha anterior...")
            time.sleep(600)
        else:
            time.sleep(60)

if __name__ == "__main__":
    run_schedule()
