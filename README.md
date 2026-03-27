# 🐿️ nf-plugin-hoarder

_nf-plugin-hoarder_ is a utility to fetch and version-sort available [Nextflow plugins](https://docs.seqera.io/nextflow/plugins/) and download them.

Mind that plugin hoarding is an anti-pattern discouraged by the Nextflow maintainers. Ideally, you should [pin plugin versions in your workflow's configuration](https://docs.seqera.io/nextflow/plugins/using-plugins#configuration) to an available version. If a certain plugin version is not yet available, it will be downloaded when launching the workflow for the first time.

However, this recommendation falls short, when there are roughly 30 workflows, each with multiple versions, run by different users on an air-gapped HPC environment that cannot download plugins at runtime. People will pin the wrong plugin version, omit pinning, want to try new plugins etc. and suddenly hoarding a reasonable amount of plugins with multiple recent versions becomes surprisingly sensible to reduce support requests. This script facilitates exactly that.

## Getting started

### Quick start using uv

The easiest way to run the hoarder without managing Python environments is using [`uv`](https://github.com/astral-sh/uv) as it will automatically handle the script's dependency.

To download the latest 3 versions of selected plugins and archive them for easier transfer:

```Bash
uv run nf_plugin_hoarder.py -p nf-schema nf-tower nf-prov -n 3 -a -c
```

You can also directly run the plugin hoarder from the repository

```Bash
uv run https://raw.githubusercontent.com/MatthiasZepper/nf_plugin_hoarder/main/nf_plugin_hoarder.py -p nf-schema nf-tower nf-prov -n 3 -a -c
```

### Proper setup with pixi

If you prefer [`pixi`](https://pixi.prefix.dev/latest/), you can create a reproducible environment that includes both Python dependencies and Nextflow itself:

- Initialize pixi:

    ```Bash
    pixi init
    pixi add python packaging nextflow
    ```

    Run the hoarder:

    ```Bash
    pixi run python nf_plugin_hoarder.py --archive --clean
    ```

## Usage options

| Flag               | Description                                         | Default                   |
|--------------------|-----------------------------------------------------|---------------------------|
| `-p, --plugins`    | Space-separated list of plugin IDs                  | nf-validation nf-tower    |
| `-n, --limit`      | Number of latest versions to download per plugin    | 5                         |
| `-o, --outdir`     | Local directory to store downloads                  | ./nxf-plugin-cache        |
| `-a, --archive`    | Create a `.tar.gz` tarball for easy transfer        | False                     |
| `-c, --clean`      | Delete the outdir after successful archiving        | False                     |

## Moving to the offline HPC

Once you have generated your nxf-plugins-offline-YYYYMMDD.tar.gz, transfer the tarball to your HPC. Extract it into an appropriate location, e.g. your default Nextflow plugin directory:

 ```Bash
    mkdir -p ~/.nextflow
    tar -xzvf nxf-plugins-offline-*.tar.gz -C ~/.nextflow/plugins/
 ```

In case you choose a non-standard location, you need to set `$NXF_PLUGINS_DIR` in your environment:

```Bash
    export NXF_PLUGINS_DIR=$HOME/.nextflow/nxf-plugin-cache
```

## Typical error message when plugins are not found

```Bash
Mar-26 17:42:11.677 [main] DEBUG nextflow.plugin.PluginsFacade - Plugins default=[nf-tower@1.17.1]
Mar-26 17:42:11.678 [main] DEBUG nextflow.plugin.PluginsFacade - Plugins resolved requirement=[nf-validation@1.1.3, nf-tower@1.17.1]
Mar-26 17:46:34.730 [main] DEBUG io.seqera.http.HxClient - HTTP request retry attempt 1: null
Mar-26 17:50:57.134 [main] DEBUG io.seqera.http.HxClient - HTTP request retry attempt 2: null
Mar-26 17:55:19.808 [main] DEBUG io.seqera.http.HxClient - HTTP request retry attempt 3: null
Mar-26 17:59:44.266 [main] DEBUG io.seqera.http.HxClient - HTTP request retry attempt 4: null
Mar-26 18:04:07.081 [main] DEBUG io.seqera.http.HxClient - HTTP request retry attempt 5: null
Mar-26 18:04:07.234 [main] ERROR nextflow.cli.Launcher - Conversion = '4'
java.util.UnknownFormatConversionException: Conversion = '4'
        at java.base/java.util.Formatter.parse(Formatter.java:2852)
        at java.base/java.util.Formatter.format(Formatter.java:2774)
        at java.base/java.util.Formatter.format(Formatter.java:2728)
        at java.base/java.lang.String.format(String.java:4386)
        at org.pf4j.util.StringUtils.format(StringUtils.java:39)
        at org.pf4j.PluginRuntimeException.<init>(PluginRuntimeException.java:41)
        at nextflow.plugin.HttpPluginRepository.fetchMetadata0(HttpPluginRepository.groovy:140)
        at nextflow.plugin.HttpPluginRepository.fetchMetadata(HttpPluginRepository.groovy:123)
        at nextflow.plugin.HttpPluginRepository.prefetch(HttpPluginRepository.groovy:70)
        at nextflow.plugin.PluginUpdater.prefetchMetadata(PluginUpdater.groovy:154)
        at nextflow.plugin.PluginsFacade.start(PluginsFacade.groovy:398)
        at nextflow.plugin.PluginsFacade.load(PluginsFacade.groovy:291)
        at nextflow.plugin.Plugins.load(Plugins.groovy:50)
        at nextflow.cli.CmdRun.run(CmdRun.groovy:363)
        at nextflow.cli.Launcher.run(Launcher.groovy:515)
        at nextflow.cli.Launcher.main(Launcher.groovy:675)
``` 