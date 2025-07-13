#include <iostream>
#include <vector>
#include <memory>
#include <thread>
#include <mutex>
#include <stdexcept>

template<typename T>
class SafeVector {
    std::vector<T> data;
    std::mutex mtx;
public:
    void add(T value) {
        std::lock_guard<std::mutex> lock(mtx);
        data.push_back(value);
    }

    T get(size_t index) {
        std::lock_guard<std::mutex> lock(mtx);
        if (index >= data.size()) throw std::out_of_range("Index out of range");
        return data[index];
    }

    size_t size() {
        std::lock_guard<std::mutex> lock(mtx);
        return data.size();
    }
};

void worker(std::shared_ptr<SafeVector<int>> vec, int start, int end) {
    for (int i = start; i < end; ++i) {
        vec->add(i);
    }
}

int main() {
    auto vec = std::make_shared<SafeVector<int>>();
    std::vector<std::thread> threads;

    for (int i = 0; i < 4; ++i) {
        threads.emplace_back(worker, vec, i * 25, (i + 1) * 25);
    }

    for (auto& t : threads) {
        t.join();
    }

    try {
        std::cout << "Element at 10: " << vec->get(10) << std::endl;
        std::cout << "Element at 100: " << vec->get(100) << std::endl; // Will throw
    } catch (const std::exception& ex) {
        std::cerr << "Exception: " << ex.what() << std::endl;
    }

    std::cout << "Total elements: " << vec->size() << std::endl;
    return 0;
}