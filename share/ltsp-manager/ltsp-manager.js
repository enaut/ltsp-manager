// Fix apturl
lockPref("network.protocol-handler.app.apt","/usr/bin/apturl");
lockPref("network.protocol-handler.warn-external.apt",false);
lockPref("network.protocol-handler.app.apt+http","/usr/bin/apturl");
lockPref("network.protocol-handler.warn-external.apt+http",false);
lockPref("network.protocol-handler.external.apt",true);
lockPref("network.protocol-handler.external.apt+http",true);

// Disable internal PDF viewer
lockPref("pdfjs.disabled",true);

// Enable flash on file:// URLs
lockPref("plugins.http_https_only",false);
