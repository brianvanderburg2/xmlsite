<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:mrbavii="urn:mrbavii:xmlsite"
    xmlns="http://www.w3.org/1999/xhtml">

    <xsl:output indent="yes" method="xml" omit-xml-declaration="no" encoding="utf-8" />

    <xsl:template match="record">
        <h1><xsl:value-of select="@name" /> - <xsl:value-of select="mrbavii:base-uri()" /> - <xsl:value-of select="mrbavii:rbase-uri()" /></h1>
        <hr />
    </xsl:template>

    <xsl:template match="/document">
        <html>
        <body>
        <xsl:apply-templates />
        </body>
        </html>
    </xsl:template>

</xsl:stylesheet>

