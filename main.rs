fn hello_world() -> &'static str {
    "hello world"
}

fn main() {
    println!("{}", hello_world());
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hello_world() {
        assert_eq!(hello_world(), "hello world");
    }
}
