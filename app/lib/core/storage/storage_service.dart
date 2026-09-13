import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../../app/config/app_config.dart';

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) {
  throw UnimplementedError('sharedPreferencesProvider must be overridden');
});

final storageServiceProvider = Provider<StorageService>((ref) {
  final prefs = ref.watch(sharedPreferencesProvider);
  return StorageService(prefs);
});

class StorageService {
  final SharedPreferences _prefs;

  StorageService(this._prefs);

  String getServerUrl() {
    return _prefs.getString(AppConfig.keyServerUrl) ?? AppConfig.defaultServerUrl;
  }

  Future<bool> setServerUrl(String url) {
    return _prefs.setString(AppConfig.keyServerUrl, url.trim());
  }

  String? getAuthToken() {
    return _prefs.getString(AppConfig.keyAuthToken);
  }

  Future<bool> setAuthToken(String token) {
    return _prefs.setString(AppConfig.keyAuthToken, token);
  }

  Future<bool> removeAuthToken() {
    return _prefs.remove(AppConfig.keyAuthToken);
  }

  String? getUserData() {
    return _prefs.getString(AppConfig.keyUserData);
  }

  Future<bool> setUserData(String jsonString) {
    return _prefs.setString(AppConfig.keyUserData, jsonString);
  }

  Future<bool> removeUserData() {
    return _prefs.remove(AppConfig.keyUserData);
  }

  Future<void> clearSession() async {
    await removeAuthToken();
    await removeUserData();
  }
}
