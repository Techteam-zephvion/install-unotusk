class SecretSanitizer {
  static final _dbUriRegex = RegExp(
    r'''(postgresql(?:\+asyncpg)?:\/\/[^\s:]+:)(.+)(@[a-zA-Z0-9_.-]+(?::[0-9]+)?(?:\/[^\s"'<>]*)?)''',
    caseSensitive: false,
  );

  static final _keyValueRegex = RegExp(
    r'''((?:api[_-]?key|token|auth[_-]?secret|password|secret)\s*[:=]\s*)["']?([^"'\s,;]{4,})["']?''',
    caseSensitive: false,
  );

  static final _groqKeyRegex = RegExp(
    r'gsk_[A-Za-z0-9_]{10,}',
    caseSensitive: false,
  );

  static final _anthropicKeyRegex = RegExp(
    r'sk-ant-[A-Za-z0-9_.-]{10,}',
    caseSensitive: false,
  );

  static String sanitize(String input) {
    var output = input;

    // Redact DB URIs: postgresql://user:PASSWORD@host:port/db
    output = output.replaceAllMapped(
      _dbUriRegex,
      (Match match) => '${match.group(1)}[REDACTED]${match.group(3)}',
    );

    // Redact key=value pairs: AUTH_SECRET="...", api_key=..., password: ...
    output = output.replaceAllMapped(
      _keyValueRegex,
      (Match match) => '${match.group(1)}[REDACTED]',
    );

    // Redact raw Groq API keys
    output = output.replaceAll(_groqKeyRegex, '[REDACTED]');

    // Redact raw Anthropic API keys
    output = output.replaceAll(_anthropicKeyRegex, '[REDACTED]');

    return output;
  }
}
