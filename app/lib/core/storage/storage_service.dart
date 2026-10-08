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

  String? getSavedEmail() => _prefs.getString('saved_email');
  Future<bool> setSavedEmail(String email) => _prefs.setString('saved_email', email);
  
  String? getSavedPassword() => _prefs.getString('saved_password');
  Future<bool> setSavedPassword(String password) => _prefs.setString('saved_password', password);

  Future<void> clearSession() async {
    await removeAuthToken();
    await removeUserData();
    await _prefs.remove('saved_email');
    await _prefs.remove('saved_password');
    await _prefs.remove(AppConfig.keyServerUrl);
  }
}
