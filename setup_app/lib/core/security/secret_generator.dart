import 'dart:math';

class SecretGenerator {
  static final Random _secureRandom = Random.secure();

  static String generateHexSecret([int byteLength = 32]) {
    final values = List<int>.generate(byteLength, (i) => _secureRandom.nextInt(256));
    return values.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  }
}
