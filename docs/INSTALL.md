# Instalação e ativação

O launcher **Atelier** já está instalado. Abra pelo menu de aplicativos ou rode:

```bash
/home/znyder/Projects/omarchy-wallpaper-manager/activate-and-run
```

O PySide6 6.12.0 já foi encontrado e validado. A primeira abertura em sua sessão
gráfica executa os testes reais do runtime, cria um novo backup validado, instala
somente a ponte do plugin e aguarda sua confirmação. Se o hot reload mantiver
a versão antiga em memória, usa uma reinicialização controlada por
`omarchy restart shell`, que pode fazer a barra e os fundos reaparecerem. Em caso de falha, o ativador
tenta o rollback protegido e exibe o erro. Nenhum pacote ou atualização é instalado.
Nas próximas aberturas o ativador detecta a ponte e apenas abre o aplicativo.

A sessão do agente não possui acesso aos sockets gráficos. Assim, a janela não
foi iniciada nela e a integração ainda não foi substituída. A instalação no usuário
e os testes offscreen estão concluídos. O comando acima deve rodar em um terminal
normal do desktop, ou pelo launcher, como fluxo normal do aplicativo.

Para avaliar apenas a biblioteca sem ativar a ponte, use `./run-atelier`.
Para a demonstração com dados fictícios, use `./run-demo`.

O aplicativo fica no diretório atual do projeto; não o mova depois da ativação.
O gerenciador anterior, shell.json e os temas personalizados são preservados.
O backup da preparação atual é:
`/home/znyder/configs/backups/atelier-functional-20261030T035916Z/`.

## Verificação e reversão

```bash
omarchy-shell background atelierCapabilities
python tools/diagnose.py
```

O registro da ativação e seu backup ficam em `~/.local/share/atelier/activation.json`.
Erros da primeira abertura ficam em `~/.local/share/atelier/activation.log`.
Veja RECOVERY.md para a reversão. O ativador não faz reinício de sessão ou remoção
do gerenciador antigo. Os testes físicos restantes estão em VALIDATION.md.

## Manutenção

`tools/prepare_migration.py` prepara um candidato apenas a partir do plugin antigo.
Não o execute sobre uma ponte já instalada. O plano usa hashes e recusa sobrescrever
mudanças inesperadas. A ativação usa o plano já preparado e validado nesta instalação.

```bash
python tools/diagnose.py --baseline   # registrar depois da validação completa
python tools/diagnose.py              # consultar após uma atualização normal
```

O diagnóstico sem --baseline não grava nem executa reparos automáticos.
