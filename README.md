# Atelier

Aplicação desktop de wallpapers e temas para o Omarchy, com a identidade visual
aprovada. Versão 0.3.0: **instalada no launcher; ativação da ponte na primeira abertura**.
O gerenciador anterior e seu plugin continuam intactos.

## Executar

```bash
cd /home/znyder/Projects/omarchy-wallpaper-manager
./run-demo       # dados simulados, sem integração
./run-atelier    # biblioteca real, aplicação no desktop bloqueada
```

O modo real permite favoritos, importações para a biblioteca privada e rascunhos
de temas. Ele não aplica wallpapers, políticas globais ou temas sem
`--enable-desktop`. Essa opção é reservada à validação autorizada e à migração.
Não use o executor QML como substituto do Python no modo real: ele não conecta
os serviços.

PySide6 **6.12.0 está disponível** no Python do sistema. O teste real de
runtime passou, incluindo a janela QML e o provedor de miniaturas.

Procure **Atelier** no launcher ou execute:

```bash
./activate-and-run
```

Na primeira abertura na sessão gráfica, o ativador verifica os monitores, repete
os testes do runtime, faz backup validado e instala a ponte. Se a shell não
confirmar a ponte, tenta a reversão protegida. Nas aberturas seguintes inicia
normalmente a aplicação. Nenhuma atualização ou instalação de pacote é executada.

O launcher já foi registrado em `~/.local/share/applications/atelier.desktop`.
Esta sessão do agente não pôde abrir a janela no desktop: o sandbox bloqueou
os sockets gráficos e a execução fora dele foi rejeitada pela política automática.
A biblioteca real foi renderizada e inspecionada em modo offscreen.

## Implementação disponível

- Descoberta de imagens locais, temas e overlays; Workshop nas bibliotecas Steam
  declaradas em `libraryfolders.vdf`.
- Pesquisa, origem, tipo, favoritos persistentes e galeria progressiva de 48 itens.
- Miniaturas assíncronas sob demanda, cache persistente limitado a 256 MiB.
- Painel contextual, escolha de monitor e encaminhamento à ponte v1 preparada.
- Preferências versionadas, escrita atômica, backups e campos legados preservados.
- Importação por cópia, sem sobrescrita; remoção recuperável somente de imagens
  importadas, impedindo remover imagens aplicadas e arquivos do Workshop.
- Leitura/edição das cores reais, campos TOML desconhecidos preservados, comparação,
  reversão, duplicação, renomeação e salvamento como novo rascunho.
- Gerador de paletas anterior reutilizado sem aplicação durante a edição.
- Adaptador de aplicação de cores que protege `default` e preserva a galeria atual.
- Diagnóstico de versões, dependências, monitores, capacidades, logs e alterações
  desde uma baseline opcional.

A aplicação e o provedor PySide6 foram executados em modo offscreen, com a
biblioteca real de 252 wallpapers e 24 temas. A aplicação de fundos e temas na
sessão gráfica ainda depende da primeira ativação pelo usuário. Não confundir
o teste offscreen com validação completa do desktop.

## Arquitetura

- `ui/Main.qml`: interface compartilhada; `DemoSession.qml` conserva a demonstração.
- `ui/LiveSession.qml`: apresentação dos dados e comandos assíncronos do Python.
- `atelier/core.py`: catálogo, preferências, temas e adaptadores.
- `atelier/service.py`: operações da aplicação.
- `atelier/qt.py`: fila serial de trabalho, sinais e provedor de imagens Qt.
- `atelier/thumbnails.py`: cache de miniaturas reduzidas.
- `packaging/engine_bridge.py`: entrada para renderização controlada pelo plugin.
- `packaging/Background.qml`: candidato separado, ainda não instalado.

O plugin existente continua sendo o proprietário dos processos de wallpaper.
A GUI não inicia outro linux-wallpaperengine. O candidato adiciona IPC versionado,
mantém o mecanismo por monitor, remove o clique direito do **desktop** e preserva
o duplo clique esquerdo para o seletor rápido nativo. O Atelier abre pelo launcher. Menus contextuais dentro da aplicação
continuam disponíveis. Uma segunda abertura solicita foco à instância existente.

Há duas dependências de contratos internos isoladas nos adaptadores: a ponte do
plugin local e `OMARCHY_THEME_SKIP_BACKGROUND`, necessário porque o CLI instalado
não oferece uma opção pública de aplicação apenas de cores. O diagnóstico verifica
esse recurso e não tenta comandos alternativos desconhecidos.

## Testes e migração

Consulte [VALIDATION.md](docs/VALIDATION.md), [INSTALL.md](docs/INSTALL.md) e
[RECOVERY.md](docs/RECOVERY.md). A migração exige aprovação e validação gráfica;
os scripts não são executados automaticamente.

O nome Atelier usa URW Gothic Bold, preferindo Euclid Flex se instalada. A fonte
geométrica alternativa e o azul em duas tonalidades permanecem como aprovados.

## Acesso rápido pelo desktop

Duplo clique esquerdo abre o seletor nativo de wallpapers do Omarchy no monitor
clicado, como na integração anterior. O resultado é aplicado pelo mesmo plugin,
com as políticas de cores existentes. Clique direito no desktop permanece
inativo. O Atelier fica no launcher para biblioteca, temas e configurações.
O seletor nativo mantém o catálogo anterior do Workshop; a descoberta ampliada
em múltiplas bibliotecas continua disponível na biblioteca do Atelier.
