# Validação — candidata 0.3.0

## Resultados executados em 30/10/2026

| Verificação | Resultado |
|---|---|
| Serviços Python | 44 testes passaram |
| QML/Qt Quick Test | 3 cenários passaram; 9 entradas incluindo init/cleanup |
| Runtime Python/PySide6 | 1 teste real passou; sem skip |
| Descoberta na instalação real | 252 wallpapers, 143 Workshop, 24 temas |
| Extração real, sem aplicar | 28 cores geradas com o gerador anterior |
| Cache real em diretório temporário | PNG de 200702 bytes gerado |
| Sintaxe Python e shell | Verificadas |
| Instalação e rollback | Testados em home temporária, sem integração real |
| Desktop e monitores físicos | Não testados; socket Hyprland inacessível nesta sessão |

Os casos cobrem múltiplas bibliotecas Steam simuladas, metadados incompatíveis,
travessia de caminhos, arquivos corrompidos e versões futuras de preferências,
escritas concorrentes, migração sem perda, reinício dos serviços, monitor ausente,
falhas/timeouts, aplicação simulada via IPC, proteção de default, preservação de
campos TOML, overlays, importação e lixeira, thumbnails e reversão protegida.

Os cenários QML cobrem o painel com cliques e redimensionamento, a comunicação da
apresentação com um backend simulado e os métodos da ponte com uma shell simulada.
Esses testes não reproduzem Quickshell/Wayland nem verificam renderização animada.

## Versões identificadas

- Omarchy 4.0.6-1.
- Hyprland 0.56.2-4.
- Quickshell 0.3.2.r7.g2b4501a-1.
- linux-wallpaperengine-git r643.a0ddce58-1.
- Python 3.14; PySide6 6.12.0; ferramentas Qt Quick Test 6.12.0.

O `--help` do renderizador instalado confirma os argumentos usados pelo adaptador.
Isso não prova que todos os projetos do Workshop sejam suportados pelo motor.
O diagnóstico completo local está em [real-check.json](real-check.json).

## Repetir os testes

A partir da raiz do projeto:

```bash
python -m unittest discover -s tests/core -v
QT_QPA_PLATFORM=offscreen QT_QPA_PLATFORMTHEME= QT_QUICK_BACKEND=software \
  /usr/lib/qt6/bin/qmltestrunner -input tests/ui -o -,txt
python -m unittest discover -s tests/qt -v
python tools/diagnose.py
```

O último conjunto deve executar efetivamente, sem skip, antes da aprovação gráfica.
O teste do runtime inclui os serviços reais em home temporária, criação da janela
e o provedor de miniaturas; ele não aplica temas nem inicia renderizadores.
A implementação do provedor segue o contrato de
[QQuickImageProvider](https://doc.qt.io/qtforpython-6/PySide6/QtQuick/QQuickImageProvider.html).

## Roteiro obrigatório na sessão gráfica

Esta etapa requer aprovação antes de ativar o candidato do plugin.

1. Instalar/disponibilizar PySide6 e passar `tests/qt` sem skip.
2. Abrir `./run-atelier`: conferir biblioteca real, thumbnails, filtros, favoritos,
   importação, editor e diagnóstico. Fechar/reabrir e confirmar persistência.
3. Verificar novamente os hashes da integração e preparar/revisar o patch.
4. Após autorização, ativar a integração candidata com backup validado.
5. Aplicar uma imagem estática em cada monitor. Conferir que só o monitor escolhido
   mudou e que a seleção é persistida.
6. Aplicar uma cena e um vídeo em monitores diferentes; confirmar o limite de um
   processo do motor por monitor. Repetir a mesma escolha e trocar rapidamente.
7. Testar as políticas default, automática, manter cores e paleta de outro tema;
   conferir as exceções e restaurar default sem alterar seu arquivo.
8. Testar seleção de monitor, desconexão/reconexão e indisponibilidade da shell.
9. Conferir duplo clique esquerdo, ausência de clique direito no desktop, abertura
   pelo launcher e foco da instância existente.
10. Fechar/reabrir o app, reiniciar a shell com autorização e depois encerrar/entrar
    na sessão para confirmar a recuperação dos renderizadores e preferências.
11. Exercitar rollback e confirmar retorno da integração anterior.
12. Somente então aprovar o Atelier como gerenciador definitivo.

## Limitações conhecidas

- O runtime PySide6 passou em modo offscreen. A validação na sessão gráfica e
  a confirmação real da ponte estão pendentes da primeira abertura pelo launcher.
- Detecção de hotplug é feita ao atualizar e novamente antes de aplicar; não há
  polling contínuo. Um monitor salvo que desapareceu exige nova seleção.
- Temas sem colors.toml não entram no editor; nenhum arquivo antigo é convertido
  automaticamente. Os 24 temas reconhecidos nesta instalação têm colors.toml.
- Cenas web/aplicações do Workshop não são reproduzidas; somente scene/video.
- Uma troca de cores cria um tema transportador próprio, preservando os fundos.
  Esses transportadores ficam ocultos da galeria e são mantidos para recuperação;
  ainda não há coleta automática deles ou dos backups.
- A lixeira de temas e imagens é recuperável pelos arquivos locais; não há uma
  página visual de lixeira. A recuperação está documentada.
- Salvar rascunhos preserva os valores TOML desconhecidos, mas reserializa o arquivo;
  comentários e formatação originais permanecem apenas no tema de origem.
- Os avisos remanescentes do qmllint são de escopo/contexto dinâmico, não erros de
  sintaxe; a ponte Python precisa da validação de execução prevista acima.

## Preservação ao encerrar a preparação

Foram comparados 77 arquivos relevantes com o backup anterior. O tema default,
os scripts antigos e o plugin instalado conferem. Dois arquivos mudaram durante
a execução, sem gravações por este trabalho: `shell.json` passou a indicar a barra
transparente, e `background-monitors.json` registra outras escolhas de wallpapers.
Essas alterações do ambiente foram preservadas. A migração fará outro backup do
estado vigente, sem restaurar o estado antigo sobre esses ajustes.

A pasta de dados real `~/.local/share/atelier` ainda não havia sido criada nesta
validação: os testes de gravação foram realizados em diretórios temporários.

## Atualização da instalação

O launcher foi instalado em 30/10/2026, com backup em
`/home/znyder/configs/backups/atelier-functional-20261030T035916Z/`.
A primeira abertura executa `tools/activate.py`, que testa o runtime, instala a
ponte e verifica sua resposta, com reversão protegida em caso de falha.
Foram acrescentados 4 testes do ativador (já ativo, sucesso, ausência de confirmação
e mudança externa no plugin). Todos passaram em ambiente temporário.

A renderização real offscreen mostrou os 252 wallpapers e 24 temas, com imagens
carregadas pelo provedor assíncrono. Captura em `docs/real-library.png`.
O acesso gráfico direto foi negado pelo sandbox (EPERM), e a solicitação de
execução fora dele foi rejeitada automaticamente. Não foi utilizado outro canal
para contornar essa restrição. A ponte instalada continua sendo a versão anterior
até a primeira abertura autorizada pelo usuário no launcher.

## Correção da espera de inicialização — 30/10/2026

Uma tentativa de ativação falhou antes de instalar a ponte: o teste usava um
loop Python com QTest.qWait, que podia atrasar a thread do backend e exceder os
cinco segundos. A espera passou a usar QEventLoop com sinal de conclusão e prazo
máximo de 20 segundos. A verificação de busy e os testes de conteúdo permanecem;
nenhum teste foi removido ou ignorado. A limpeza da janela e do executor ocorre
em finally, inclusive em falhas.

O teste passou por unittest e pela invocação -c usada pelo instalador. O diálogo
de falha agora escapa o texto para impedir que nomes como <module> sejam tratados
como marcação GTK; um teste de regressão cobre a mensagem e o log original.
O plano de migração foi regenerado e agora inclui o hash dos testes Qt.

## Ponte ausente após hot reload — 30/10/2026

Os logs da shell registraram recargas do plugin às 01:05, mas a consulta da
ponte não confirmou a versão instalada. O rollback restaurou o arquivo anterior
e removeu o launcher, conforme seu comportamento antigo. Não houve confirmação
da nova ponte no desktop nesta sessão do agente.

A ativação agora tenta hot reload e depois uma reinicialização pelo comando
oficial `omarchy restart shell`. Esse comando aguarda o encerramento das instâncias
anteriores e respeita o bloqueio da sessão. Se a confirmação continuar falhando,
a reversão preserva o launcher e tenta restaurar a shell com o plugin anterior.
A resposta concreta do IPC é incluída no erro; JSON encapsulado em string também
é aceito. O launcher removido pelo rollback anterior foi reinstalado.

49 testes Python passaram, incluindo shell antiga em memória, falha persistente,
recusa de reinicialização e detalhes de erro IPC. O teste real PySide6 também
passou. Os novos casos de reinicialização usam comandos simulados; a confirmação
real será feita na próxima execução na sessão gráfica do usuário.

## Rolagem da biblioteca — 30/10/2026

Corrigida a altura explícita do conteúdo nas galerias de wallpapers e temas.
O ScrollView tinha dois filhos visuais (grade e mensagem vazia), impedindo a
inferência automática da altura total. O teste de regressão reproduziu a falha
antes da alteração e passou depois. Cobertura: roda do mouse sobre miniaturas,
painel contextual aberto/fechado, acesso a Carregar mais e rolagem de temas.
A alteração é apenas QML; a ponte instalada não foi substituída ou reiniciada.
Fechar e reabrir o Atelier carrega a correção.

## Seletor rápido restaurado — 30/10/2026

A pedido do usuário, o duplo clique no desktop volta ao seletor nativo anterior,
sem abrir o Atelier. O helper reutiliza picker.py para a seleção e encaminha seu
JSON ao plugin existente. Renderização, monitor e políticas permanecem na ponte
atual; clique direito continua desativado. O gerador de futuras instalações
preserva o seletor nativo.

Três testes passaram: encaminhamento do resultado, cancelamento sem iniciar
renderizador e contrato do clique no candidato QML. A sintaxe QML foi validada.
O arquivo instalado recebeu backup em `backups/quick-picker-20261030T041630Z`.
O registro do rollback da migração ativa foi atualizado após conferir o hash
anterior. Nenhum tema ou preferência de wallpaper foi alterado.
A recarga visual na sessão do usuário ainda precisa ocorrer; se o componente
estiver em cache, `omarchy restart shell` carrega a nova versão.
